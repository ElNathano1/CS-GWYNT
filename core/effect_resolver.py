"""Effect resolution helpers for the game loop."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import TYPE_CHECKING

from .effect import (
    Effect,
    EffectType,
    Event,
    MoveTarget,
    SwapTarget,
    Target,
    TargetType,
    Targets,
)
from .lane import LaneType

if TYPE_CHECKING:
    from .card import Card
    from .game import Game
    from .player import Player


@dataclass
class EffectResolution:
    """Structured report of an effect resolution pass."""

    event: Event
    source_card_id: int | None
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    missing_choices: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResolutionChoices:
    """Optional explicit target choices provided by the player/UI."""

    card_choices: dict[str, int | list[int]] = field(default_factory=dict)
    lane_choices: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, object] | None) -> "ResolutionChoices":
        if not isinstance(payload, dict):
            return cls()

        raw_card_choices = payload.get("card_choices")
        card_choices = raw_card_choices if isinstance(raw_card_choices, dict) else {}

        raw_lane_choices = payload.get("lane_choices")
        lane_choices = raw_lane_choices if isinstance(raw_lane_choices, dict) else {}

        return cls(
            card_choices={str(k): v for k, v in card_choices.items()},
            lane_choices={str(k): str(v) for k, v in lane_choices.items()},
        )

    def get_card_ids(self, selector: Targets) -> list[int]:
        raw = self.card_choices.get(selector.value)
        if isinstance(raw, int):
            return [raw]
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, int)]
        return []

    def get_lane(self, selector: Targets) -> LaneType | None:
        raw = self.lane_choices.get(selector.value)
        if raw is None:
            return None
        try:
            return LaneType(raw)
        except ValueError:
            return None

    def has_card_choice(self, selector: Targets) -> bool:
        return selector.value in self.card_choices

    def has_lane_choice(self, selector: Targets) -> bool:
        return selector.value in self.lane_choices


CARD_CHOICE_SELECTORS = {
    Targets.CARD,
    Targets.ALLY,
    Targets.ENEMY,
    Targets.ADJACENT,
    Targets.RANDOM_CARD_ON_LANE,
    Targets.RANDOM_CARD_ON_ALLY_LANE,
    Targets.RANDOM_CARD_ON_ENEMY_LANE,
    Targets.CARD_IN_HAND,
    Targets.CARD_IN_ENEMY_HAND,
    Targets.CARD_IN_DECK,
    Targets.CARD_IN_ENEMY_DECK,
    Targets.CARD_IN_DISCARD,
    Targets.CARD_IN_ENEMY_DISCARD,
}

LANE_CHOICE_SELECTORS = {
    Targets.LANE,
    Targets.ALLY_LANE,
    Targets.ENEMY_LANE,
}


class EffectResolver:
    """Apply triggered effects to the mutable game state."""

    @staticmethod
    def _register_missing_choice(
        report: EffectResolution,
        selector: Targets,
        kind: str,
    ) -> None:
        report.missing_choices.append(
            f"Missing {kind} choice for target '{selector.value}'"
        )

    def resolve_on_play(
        self,
        game: "Game",
        source_player: "Player",
        source_card: "Card",
        choices: ResolutionChoices | None = None,
    ) -> EffectResolution:
        report = EffectResolution(
            event=Event.ON_PLAY,
            source_card_id=getattr(source_card, "id", None),
        )

        effect = getattr(source_card, "effect", None)
        if effect is None:
            report.skipped.append("No effect on source card")
            return report

        if not effect.trigger.should_trigger(
            Event.ON_PLAY,
            source_player,
            source_card,
            game,
        ):
            report.skipped.append("Trigger conditions not met")
            return report

        try:
            self.apply_effect(
                game,
                source_player,
                source_card,
                effect,
                report,
                choices or ResolutionChoices(),
            )
        except Exception as exc:
            report.errors.append(f"Effect failed: {exc}")

        game.player1.update_power()
        if game.player2 is not None:
            game.player2.update_power()

        return report

    def apply_effect(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        match effect.effect_type:
            case EffectType.BUFF:
                self._apply_buff(game, owner, source_card, effect, report, choices)
            case EffectType.MULTIPLY_POWER:
                self._apply_multiply_power(
                    game,
                    owner,
                    source_card,
                    effect,
                    report,
                    choices,
                )
            case EffectType.SET_POWER:
                self._apply_set_power(
                    game,
                    owner,
                    source_card,
                    effect,
                    report,
                    choices,
                )
            case EffectType.DESTROY:
                self._apply_destroy(game, owner, source_card, effect, report, choices)
            case EffectType.DRAW:
                owner.draw_card()
                report.applied.append("Owner draws one card")
            case EffectType.DISCARD:
                self._apply_discard(game, owner, source_card, effect, report, choices)
            case EffectType.MOVE | EffectType.SUMMON:
                self._apply_move(game, owner, source_card, effect, report, choices)
            case EffectType.SWAP_POWER:
                self._apply_swap_power(
                    game,
                    owner,
                    source_card,
                    effect,
                    report,
                    choices,
                )
            case EffectType.SWAP_POSITION:
                self._apply_swap_position(
                    game,
                    owner,
                    source_card,
                    effect,
                    report,
                    choices,
                )
            case _:
                report.skipped.append(
                    f"Effect type not implemented yet: {effect.effect_type.value}"
                )

    def _all_board_cards(self, game: "Game") -> list[tuple["Player", str, "Card"]]:
        rows: list[tuple["Player", str, "Card"]] = []
        players = [game.player1] + ([game.player2] if game.player2 is not None else [])
        for player in players:
            for lane_name, lane in player.board.items():
                for card in lane:
                    rows.append((player, lane_name, card))
        return rows

    def _cards_for_target(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        target: Target,
        choices: ResolutionChoices,
    ) -> list["Card"]:
        board_rows = self._all_board_cards(game)
        allies = [card for player, _, card in board_rows if player == owner]
        enemies = [card for player, _, card in board_rows if player != owner]
        all_cards = [card for _, _, card in board_rows]

        selector = target.selector

        def chosen_cards(source_cards: list["Card"]) -> list["Card"]:
            chosen_ids = set(choices.get_card_ids(selector))
            if not chosen_ids:
                return []
            return [card for card in source_cards if card.id in chosen_ids]

        if selector == Targets.CARD:
            return chosen_cards(all_cards)

        if selector == Targets.ALLY:
            return chosen_cards(allies)

        if selector == Targets.ENEMY:
            return chosen_cards(enemies)

        if selector == Targets.ADJACENT:
            if source_card.current_lane is None:
                return []
            lane = owner.board[source_card.current_lane.value]
            if source_card not in lane:
                return []
            index = lane.index(source_card)
            adjacent: list["Card"] = []
            if index - 1 >= 0:
                adjacent.append(lane[index - 1])
            if index + 1 < len(lane):
                adjacent.append(lane[index + 1])
            return chosen_cards(adjacent)

        if selector == Targets.RANDOM_CARD_ON_LANE:
            chosen_lane = choices.get_lane(selector)
            if chosen_lane is None:
                return []
            lane_cards = [
                card
                for _, lane_name, card in board_rows
                if lane_name == chosen_lane.value
            ]
            return [random.choice(lane_cards)] if lane_cards else []

        if selector == Targets.RANDOM_CARD_ON_ALLY_LANE:
            chosen_lane = choices.get_lane(selector)
            if chosen_lane is None:
                return []
            lane_cards = [
                card
                for player, lane_name, card in board_rows
                if lane_name == chosen_lane.value and player == owner
            ]
            return [random.choice(lane_cards)] if lane_cards else []

        if selector == Targets.RANDOM_CARD_ON_ENEMY_LANE:
            chosen_lane = choices.get_lane(selector)
            if chosen_lane is None:
                return []
            lane_cards = [
                card
                for player, lane_name, card in board_rows
                if lane_name == chosen_lane.value and player != owner
            ]
            return [random.choice(lane_cards)] if lane_cards else []

        if selector == Targets.CARD_IN_HAND:
            return chosen_cards(list(owner.hand))

        if selector == Targets.CARD_IN_ENEMY_HAND and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return chosen_cards(list(enemy.hand))

        if selector == Targets.CARD_IN_DECK:
            return chosen_cards(list(owner.deck))

        if selector == Targets.CARD_IN_ENEMY_DECK and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return chosen_cards(list(enemy.deck))

        if selector == Targets.CARD_IN_DISCARD:
            return chosen_cards(list(owner.discard_pile))

        if selector == Targets.CARD_IN_ENEMY_DISCARD and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return chosen_cards(list(enemy.discard_pile))

        # Handle non-choice-based selectors with random/default logic
        if selector == Targets.SELF:
            return [source_card]

        if selector == Targets.RANDOM_ALLY:
            return [random.choice(allies)] if allies else []

        if selector == Targets.RANDOM_ENEMY:
            return [random.choice(enemies)] if enemies else []

        if selector == Targets.RANDOM_OTHER_ALLY:
            return (
                [random.choice([card for card in allies if card is not source_card])]
                if len(allies) > 1
                else []
            )

        if selector == Targets.RANDOM_OTHER_ENEMY:
            return (
                [random.choice([card for card in enemies if card is not source_card])]
                if len(enemies) > 1
                else []
            )

        if selector == Targets.RANDOM_CARD:
            return [random.choice(all_cards)] if all_cards else []

        if selector == Targets.ALL_ALLIES:
            return allies

        if selector == Targets.ALL_ENEMIES:
            return enemies

        if selector == Targets.ALL_OTHER_ALLIES:
            return (
                [card for card in allies if card is not source_card]
                if len(allies) > 1
                else []
            )

        if selector == Targets.ALL_OTHER_ENEMIES:
            return (
                [card for card in enemies if card is not source_card]
                if len(enemies) > 1
                else []
            )

        if selector == Targets.ALL_OTHER_CARDS:
            return [card for card in all_cards if card is not source_card]

        if selector == Targets.ALL_CARDS:
            return all_cards

        if selector == Targets.RANDOM_ADJACENT and source_card.current_lane is not None:
            lane = owner.board[source_card.current_lane.value]
            if source_card in lane:
                index = lane.index(source_card)
                adjacent: list["Card"] = []
                if index - 1 >= 0:
                    adjacent.append(lane[index - 1])
                if index + 1 < len(lane):
                    adjacent.append(lane[index + 1])
                return [random.choice(adjacent)] if adjacent else []
            return []

        if selector == Targets.ALL_CARDS_ON_OTHER_ALLY_LANES:
            source_lane = (
                source_card.current_lane.value
                if source_card.current_lane is not None
                else None
            )
            return [
                card
                for player, lane_name, card in board_rows
                if player == owner and lane_name != source_lane
            ]

        if selector == Targets.ALL_CARDS_ON_OTHER_ENEMY_LANES:
            source_lane = (
                source_card.current_lane.value
                if source_card.current_lane is not None
                else None
            )
            return [
                card
                for player, lane_name, card in board_rows
                if player != owner and lane_name != source_lane
            ]

        if selector == Targets.ALL_CARDS_ON_OTHER_LANES:
            source_lane = (
                source_card.current_lane.value
                if source_card.current_lane is not None
                else None
            )
            return [
                card
                for player, lane_name, card in board_rows
                if lane_name != source_lane
            ]

        if selector == Targets.RANDOM_CARD_IN_HAND:
            return [random.choice(owner.hand)] if owner.hand else []

        if selector == Targets.RANDOM_CARD_IN_ENEMY_HAND and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return [random.choice(enemy.hand)] if enemy.hand else []

        if selector == Targets.RANDOM_CARD_IN_HANDS:
            players = [game.player1] + (
                [game.player2] if game.player2 is not None else []
            )
            all_hands = []
            for player in players:
                all_hands.extend(player.hand)
            return [random.choice(all_hands)] if all_hands else []

        if selector == Targets.NEXT_CARD_IN_DECK:
            return [owner.deck[0]] if owner.deck else []

        if selector == Targets.NEXT_CARD_IN_ENEMY_DECK and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return [enemy.deck[0]] if enemy.deck else []

        if selector == Targets.RANDOM_CARD_IN_DECK:
            return [random.choice(owner.deck)] if owner.deck else []

        if selector == Targets.RANDOM_CARD_IN_ENEMY_DECK and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return [random.choice(enemy.deck)] if enemy.deck else []

        if selector == Targets.RANDOM_CARD_IN_DECKS:
            players = [game.player1] + (
                [game.player2] if game.player2 is not None else []
            )
            all_decks = []
            for player in players:
                all_decks.extend(player.deck)
            return [random.choice(all_decks)] if all_decks else []

        if selector == Targets.RANDOM_CARD_IN_DISCARD:
            return [random.choice(owner.discard_pile)] if owner.discard_pile else []

        if (
            selector == Targets.RANDOM_CARD_IN_ENEMY_DISCARD
            and game.player2 is not None
        ):
            enemy = game.player2 if owner == game.player1 else game.player1
            return [random.choice(enemy.discard_pile)] if enemy.discard_pile else []

        if selector == Targets.RANDOM_CARD_IN_DISCARDS:
            players = [game.player1] + (
                [game.player2] if game.player2 is not None else []
            )
            all_discard_piles = []
            for player in players:
                all_discard_piles.extend(player.discard_pile)
            return [random.choice(all_discard_piles)] if all_discard_piles else []

        if selector == Targets.HAND:
            return owner.hand

        if selector == Targets.ENEMY_HAND and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return enemy.hand

        if selector == Targets.DECK:
            return owner.deck

        if selector == Targets.ENEMY_DECK and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return enemy.deck

        if selector == Targets.DISCARD:
            return owner.discard_pile

        if selector == Targets.ENEMY_DISCARD and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return enemy.discard_pile

        return []

    def _position_candidates(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        target: Target,
        choices: ResolutionChoices,
    ) -> list[tuple["Player", LaneType]]:
        selector = target.selector

        if selector == Targets.LANE:
            chosen_lane = choices.get_lane(selector)
            return [(owner, chosen_lane)] if chosen_lane is not None else []

        if selector == Targets.ALLY_LANE:
            chosen_lane = choices.get_lane(selector)
            return [(owner, chosen_lane)] if chosen_lane is not None else []

        if selector == Targets.ENEMY_LANE and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            chosen_lane = choices.get_lane(selector)
            return [(enemy, chosen_lane)] if chosen_lane is not None else []

        if selector == Targets.RANDOM_LANE:
            return [(owner, random.choice(list(LaneType)))]

        if selector == Targets.RANDOM_ALLY_LANE:
            return [(owner, random.choice(list(LaneType)))]

        if selector == Targets.RANDOM_ENEMY_LANE and game.player2 is not None:
            enemy = game.player2 if owner == game.player1 else game.player1
            return [(enemy, random.choice(list(LaneType)))]

        return []

    def _find_card_owner(self, game: "Game", card: "Card") -> "Player | None":
        if any(card in lane for lane in game.player1.board.values()):
            return game.player1
        if game.player2 is not None and any(
            card in lane for lane in game.player2.board.values()
        ):
            return game.player2
        return None

    def _relocate_card(
        self,
        game: "Game",
        card: "Card",
        destination_player: "Player",
        destination_lane: LaneType,
    ) -> bool:
        origin = self._find_card_owner(game, card)
        if origin is None:
            return False

        if card.current_lane is None:
            return False

        try:
            origin.board[card.current_lane.value].remove(card)
            destination_player.board[destination_lane.value].append(card)
            return True
        except Exception:
            return False

    def _apply_buff(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        value = effect.value
        if not isinstance(value, int):
            report.skipped.append("BUFF expects integer value")
            return

        if not isinstance(effect.target, Target):
            report.skipped.append("BUFF expects a single target selector")
            return

        if effect.target.target_type == TargetType.CARD:
            targets = self._cards_for_target(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
        elif effect.target.target_type == TargetType.POSITION:
            position_targets = self._position_candidates(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
            targets = []
            for player, lane in position_targets:
                targets.extend(player.board[lane.value])

        if not targets and effect.target.selector in CARD_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "card")
        elif not targets and effect.target.selector in LANE_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "lane")
        if not targets:
            report.skipped.append("BUFF found no target")
            return

        for card in targets:
            card.power_table += value  # type: ignore
            card.update_current_power()
        report.applied.append(f"BUFF applied to {len(targets)} card(s)")

    def _apply_multiply_power(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        value = effect.value
        if not isinstance(value, int):
            report.skipped.append("MULTIPLY_POWER expects integer value")
            return

        if not isinstance(effect.target, Target):
            report.skipped.append("MULTIPLY_POWER expects a single target selector")
            return

        if effect.target.target_type == TargetType.CARD:
            targets = self._cards_for_target(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
        elif effect.target.target_type == TargetType.POSITION:
            position_targets = self._position_candidates(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
            targets = []
            for player, lane in position_targets:
                targets.extend(player.board[lane.value])

        if not targets and effect.target.selector in CARD_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "card")
        elif not targets and effect.target.selector in LANE_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "lane")
        if not targets:
            report.skipped.append("MULTIPLY_POWER found no target")
            return

        for card in targets:
            card.power_table *= value  # type: ignore
            card.update_current_power()
        report.applied.append(f"MULTIPLY_POWER applied to {len(targets)} card(s)")

    def _apply_set_power(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        value = effect.value
        if not isinstance(value, int):
            report.skipped.append("SET_POWER expects integer value")
            return

        if not isinstance(effect.target, Target):
            report.skipped.append("SET_POWER expects a single target selector")
            return

        if effect.target.target_type == TargetType.CARD:
            targets = self._cards_for_target(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
        elif effect.target.target_type == TargetType.POSITION:
            position_targets = self._position_candidates(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
            targets = []
            for player, lane in position_targets:
                targets.extend(player.board[lane.value])

        if not targets and effect.target.selector in CARD_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "card")
        elif not targets and effect.target.selector in LANE_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "lane")
        if not targets:
            report.skipped.append("SET_POWER found no target")
            return

        for card in targets:
            card.power_table = PowerTable(value, value, value)  # type: ignore
            card.update_current_power()
        report.applied.append(f"SET_POWER applied to {len(targets)} card(s)")

    def _apply_destroy(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        if not isinstance(effect.target, Target):
            report.skipped.append("DESTROY expects a single target selector")
            return

        if effect.target.target_type == TargetType.CARD:
            targets = self._cards_for_target(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
        elif effect.target.target_type == TargetType.POSITION:
            position_targets = self._position_candidates(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
            targets = []
            for player, lane in position_targets:
                targets.extend(player.board[lane.value])

        if not targets and effect.target.selector in CARD_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "card")
        elif not targets and effect.target.selector in LANE_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "lane")
        if not targets:
            report.skipped.append("DESTROY found no target")
            return

        destroyed = 0
        for card in targets:
            card_owner = self._find_card_owner(game, card)
            if card_owner is None:
                continue
            try:
                card_owner.destroy_card(card)
                destroyed += 1
            except Exception:
                continue

        if destroyed:
            report.applied.append(f"DESTROY removed {destroyed} card(s)")
        else:
            report.skipped.append("DESTROY failed to remove targets")

    def _apply_discard(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        if not isinstance(effect.target, Target):
            report.skipped.append("DISCARD expects a single target selector")
            return

        if effect.target.target_type == TargetType.CARD:
            targets = self._cards_for_target(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
        elif effect.target.target_type == TargetType.POSITION:
            position_targets = self._position_candidates(
                game,
                owner,
                source_card,
                effect.target,
                choices,
            )
            targets = []
            for player, lane in position_targets:
                targets.extend(player.board[lane.value])

        if not targets and effect.target.selector in CARD_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "card")
        elif not targets and effect.target.selector in LANE_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.selector, "lane")
        if not targets:
            report.skipped.append("DISCARD found no target")
            return

        discarded = 0
        for card in targets:
            card_owner = self._find_card_owner(game, card)
            if card_owner is None:
                continue
            try:
                card_owner.discard_card(card)
                discarded += 1
            except Exception:
                continue

        if discarded:
            report.applied.append(f"DISCARD removed {discarded} card(s)")
        else:
            report.skipped.append("DISCARD failed to remove targets")

    def _apply_move(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        if not isinstance(effect.target, MoveTarget):
            report.skipped.append("MOVE/SUMMON expects move target")
            return

        if effect.target.source.target_type == TargetType.CARD:
            sources = self._cards_for_target(
                game,
                owner,
                source_card,
                effect.target.source,
                choices,
            )
        elif effect.target.source.target_type == TargetType.POSITION:
            position_targets = self._position_candidates(
                game,
                owner,
                source_card,
                effect.target.source,
                choices,
            )
            sources = []
            for player, lane in position_targets:
                sources.extend(player.board[lane.value])

        if not sources and effect.target.source.selector in CARD_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.source.selector, "card")
        elif not sources and effect.target.source.selector in LANE_CHOICE_SELECTORS:
            self._register_missing_choice(report, effect.target.source.selector, "lane")
        if not sources:
            report.skipped.append("MOVE/SUMMON found no source")
            return

        moved = 0
        for source in sources:

            targets = self._position_candidates(
                game,
                owner,
                source_card,
                effect.target.destination,
                choices,
            )

            if (
                not targets
                and effect.target.destination.selector in LANE_CHOICE_SELECTORS
            ):
                self._register_missing_choice(
                    report,
                    effect.target.destination.selector,
                    "lane",
                )
            if not targets:
                report.skipped.append("MOVE/SUMMON found no destination")
                return
            if len(targets) > 1:
                report.skipped.append(
                    "MOVE/SUMMON found multiple destinations, expected one"
                )
                return

            if self._relocate_card(
                game,
                source,
                targets[0][0],  # destination player
                targets[0][1],  # destination lane
            ):
                moved += 1

        if moved:
            report.applied.append(f"MOVE/SUMMON moved {moved} card(s)")
        else:
            report.skipped.append("MOVE/SUMMON found no movable targets")

    def _apply_swap_power(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        if not isinstance(effect.target, SwapTarget):
            report.skipped.append("SWAP_POWER expects swap target")
            return

        first = self._cards_for_target(
            game,
            owner,
            source_card,
            effect.target.first,
            choices,
        )
        second = self._cards_for_target(
            game,
            owner,
            source_card,
            effect.target.second,
            choices,
        )
        if (
            not first
            and effect.target.first.selector in CARD_CHOICE_SELECTORS
            and not choices.has_card_choice(effect.target.first.selector)
        ):
            self._register_missing_choice(report, effect.target.first.selector, "card")
        if (
            not second
            and effect.target.second.selector in CARD_CHOICE_SELECTORS
            and not choices.has_card_choice(effect.target.second.selector)
        ):
            self._register_missing_choice(report, effect.target.second.selector, "card")
        if not first or not second:
            report.skipped.append("SWAP_POWER found no valid pair")
            return

        first_card = first[0]
        second_card = second[0]
        first_card.current_power, second_card.current_power = (
            second_card.current_power,
            first_card.current_power,
        )
        report.applied.append("SWAP_POWER applied to one pair")

    def _apply_swap_position(
        self,
        game: "Game",
        owner: "Player",
        source_card: "Card",
        effect: Effect,
        report: EffectResolution,
        choices: ResolutionChoices,
    ) -> None:
        if not isinstance(effect.target, SwapTarget):
            report.skipped.append("SWAP_POSITION expects swap target")
            return

        first = self._cards_for_target(
            game,
            owner,
            source_card,
            effect.target.first,
            choices,
        )
        second = self._cards_for_target(
            game,
            owner,
            source_card,
            effect.target.second,
            choices,
        )
        if (
            not first
            and effect.target.first.selector in CARD_CHOICE_SELECTORS
            and not choices.has_card_choice(effect.target.first.selector)
        ):
            self._register_missing_choice(report, effect.target.first.selector, "card")
        if (
            not second
            and effect.target.second.selector in CARD_CHOICE_SELECTORS
            and not choices.has_card_choice(effect.target.second.selector)
        ):
            self._register_missing_choice(report, effect.target.second.selector, "card")
        if not first or not second:
            report.skipped.append("SWAP_POSITION found no valid pair")
            return

        card_a = first[0]
        card_b = second[0]
        owner_a = self._find_card_owner(game, card_a)
        owner_b = self._find_card_owner(game, card_b)
        lane_a = card_a.current_lane
        lane_b = card_b.current_lane
        if owner_a is None or owner_b is None or lane_a is None or lane_b is None:
            report.skipped.append("SWAP_POSITION could not resolve origins")
            return

        if not self._relocate_card(game, card_a, owner_b, lane_b):
            report.skipped.append("SWAP_POSITION failed for first card")
            return
        if not self._relocate_card(game, card_b, owner_a, lane_a):
            report.skipped.append("SWAP_POSITION failed for second card")
            return

        report.applied.append("SWAP_POSITION applied to one pair")
