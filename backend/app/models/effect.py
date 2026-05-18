"""Effect model."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from .card import Card
from .game import Game
from .player import Player
from .power import PowerTable


class EffectType(str, Enum):
    """Types of card effects."""

    BUFF = "buff"
    MULTIPLY_POWER = "multiply_power"
    SET_POWER = "set_power"
    SWAP_POWER = "swap_power"

    MOVE = "move"
    SWAP_POSITION = "swap_position"
    LOCK_POSITION = "lock_position"
    UNLOCK_POSITION = "unlock_position"

    DESTROY = "destroy"
    TRANSFORM = "transform"
    COPY = "copy"
    SUMMON = "summon"

    SHIELD = "shield"
    IMMUNITY = "immunity"
    CLEANSE = "cleanse"

    DRAW = "draw"
    DISCARD = "discard"
    SEARCH = "search"

    SILENCE = "silence"
    CANCEL = "cancel"


class TargetKind(str, Enum):
    """High-level categories for effect targets."""

    CARD = "card"
    POSITION = "position"
    CARD_CONTAINER = "card_container"


# Backward-compatible alias for existing imports and typing.
TargetType = TargetKind


class Targets(str, Enum):
    """Concrete target selectors used by effects."""

    # --  CARDS --

    # Single card targets
    SELF = "self"
    CARD = "card"
    RANDOM_CARD = "random_card"

    # Single card targets with constraints of player
    ALLY = "ally"
    ENEMY = "enemy"
    RANDOM_ALLY = "random_ally"
    RANDOM_ENEMY = "random_enemy"
    RANDOM_OTHER_ALLY = "random_other_ally"
    RANDOM_OTHER_ENEMY = "random_other_enemy"

    # Multiple card targets with constraints of player
    ALL_ALLIES = "all_allies"
    ALL_ENEMIES = "all_enemies"
    ALL_OTHER_ALLIES = "all_other_allies"
    ALL_OTHER_ENEMIES = "all_other_enemies"
    ALL_OTHER_CARDS = "all_other_cards"
    ALL_CARDS = "all_cards"

    # Single card targets with constraints of position
    ADJACENT = "adjacent"
    RANDOM_ADJACENT = "random_adjacent"
    CARD_ON_LANE = "lane"
    RANDOM_CARD_ON_LANE = "random_card_on_lane"
    CARD_ON_RANDOM_LANE = "random_lane"

    # Single card targets with constraints of both player and position
    CARD_ON_ALLY_LANE = "ally_lane"
    CARD_ON_ENEMY_LANE = "enemy_lane"
    RANDOM_CARD_ON_ALLY_LANE = "random_card_on_ally_lane"
    RANDOM_CARD_ON_ENEMY_LANE = "random_card_on_enemy_lane"
    CARD_ON_RANDOM_ALLY_LANE = "random_ally_lane"
    CARD_ON_RANDOM_ENEMY_LANE = "random_enemy_lane"

    # Multiple card targets with constraints of both player and position
    ALL_CARDS_ON_OTHER_ALLY_LANES = "all_other_ally_lanes"
    ALL_CARDS_ON_OTHER_ENEMY_LANES = "all_other_enemy_lanes"
    ALL_CARDS_ON_OTHER_LANES = "all_other_lanes"
    ALL_CARDS_ON_BOARD = "all_board"

    # Single card targets with constraints of container
    CARD_IN_HAND = "card_in_hand"
    CARD_IN_ENEMY_HAND = "card_in_enemy_hand"
    RANDOM_CARD_IN_HAND = "random_card_in_hand"
    RANDOM_CARD_IN_ENEMY_HAND = "random_card_in_enemy_hand"
    RANDOM_CARD_IN_HANDS = "random_card_in_hands"

    CARD_IN_DECK = "card_in_deck"
    CARD_IN_ENEMY_DECK = "card_in_enemy_deck"
    RANDOM_CARD_IN_DECK = "random_card_in_deck"
    RANDOM_CARD_IN_ENEMY_DECK = "random_card_in_enemy_deck"
    RANDOM_CARD_IN_DECKS = "random_card_in_decks"

    CARD_IN_DISCARD = "card_in_discard"
    CARD_IN_ENEMY_DISCARD = "card_in_enemy_discard"
    RANDOM_CARD_IN_DISCARD = "random_card_in_discard"
    RANDOM_CARD_IN_ENEMY_DISCARD = "random_card_in_enemy_discard"
    RANDOM_CARD_IN_DISCARDS = "random_card_in_discards"

    # -- POSITIONS --

    # Single position targets
    LANE = "lane"
    RANDOM_LANE = "random_lane"

    # Single position targets with constraints of player
    ALLY_LANE = "ally_lane"
    ENEMY_LANE = "enemy_lane"
    RANDOM_ALLY_LANE = "random_ally_lane"
    RANDOM_ENEMY_LANE = "random_enemy_lane"

    # Multiple position targets with constraints of player
    ALL_ALLY_LANES = "all_ally_lanes"
    ALL_ENEMY_LANES = "all_enemy_lanes"
    ALL_OTHER_ALLY_LANES = "all_other_ally_lanes"
    ALL_OTHER_ENEMY_LANES = "all_other_enemy_lanes"
    ALL_OTHER_LANES = "all_other_lanes"
    ALL_BOARD = "all_board"

    # -- CONTAINERS --

    HAND = "hand"
    ENEMY_HAND = "enemy_hand"
    DECK = "deck"
    ENEMY_DECK = "enemy_deck"
    DISCARD = "discard"
    ENEMY_DISCARD = "enemy_discard"


CARD_TARGETS = {
    Targets.SELF,
    Targets.CARD,
    Targets.RANDOM_CARD,
    Targets.ALLY,
    Targets.ENEMY,
    Targets.RANDOM_ALLY,
    Targets.RANDOM_ENEMY,
    Targets.RANDOM_OTHER_ALLY,
    Targets.RANDOM_OTHER_ENEMY,
    Targets.ALL_ALLIES,
    Targets.ALL_ENEMIES,
    Targets.ALL_OTHER_ALLIES,
    Targets.ALL_OTHER_ENEMIES,
    Targets.ALL_OTHER_CARDS,
    Targets.ALL_CARDS,
    Targets.ADJACENT,
    Targets.RANDOM_ADJACENT,
    Targets.CARD_ON_LANE,
    Targets.RANDOM_CARD_ON_LANE,
    Targets.CARD_ON_RANDOM_LANE,
    Targets.CARD_ON_ALLY_LANE,
    Targets.CARD_ON_ENEMY_LANE,
    Targets.RANDOM_CARD_ON_ALLY_LANE,
    Targets.RANDOM_CARD_ON_ENEMY_LANE,
    Targets.CARD_ON_RANDOM_ALLY_LANE,
    Targets.CARD_ON_RANDOM_ENEMY_LANE,
    Targets.ALL_CARDS_ON_OTHER_ALLY_LANES,
    Targets.ALL_CARDS_ON_OTHER_ENEMY_LANES,
    Targets.ALL_CARDS_ON_OTHER_LANES,
    Targets.ALL_CARDS_ON_BOARD,
    Targets.CARD_IN_HAND,
    Targets.CARD_IN_ENEMY_HAND,
    Targets.RANDOM_CARD_IN_HAND,
    Targets.RANDOM_CARD_IN_ENEMY_HAND,
    Targets.RANDOM_CARD_IN_HANDS,
    Targets.CARD_IN_DECK,
    Targets.CARD_IN_ENEMY_DECK,
    Targets.RANDOM_CARD_IN_DECK,
    Targets.RANDOM_CARD_IN_ENEMY_DECK,
    Targets.RANDOM_CARD_IN_DECKS,
    Targets.CARD_IN_DISCARD,
    Targets.CARD_IN_ENEMY_DISCARD,
    Targets.RANDOM_CARD_IN_DISCARD,
    Targets.RANDOM_CARD_IN_ENEMY_DISCARD,
    Targets.RANDOM_CARD_IN_DISCARDS,
}

POSITION_TARGETS = {
    Targets.LANE,
    Targets.RANDOM_LANE,
    Targets.ALLY_LANE,
    Targets.ENEMY_LANE,
    Targets.RANDOM_ALLY_LANE,
    Targets.RANDOM_ENEMY_LANE,
    Targets.ALL_ALLY_LANES,
    Targets.ALL_ENEMY_LANES,
    Targets.ALL_OTHER_ALLY_LANES,
    Targets.ALL_OTHER_ENEMY_LANES,
    Targets.ALL_OTHER_LANES,
    Targets.ALL_BOARD,
}

CONTAINER_TARGETS = {
    Targets.HAND,
    Targets.ENEMY_HAND,
    Targets.DECK,
    Targets.ENEMY_DECK,
    Targets.DISCARD,
    Targets.ENEMY_DISCARD,
}


def target_kind_for(selector: Targets) -> TargetType:
    """Return the category for a concrete selector."""

    if selector in CARD_TARGETS:
        return TargetType.CARD
    if selector in POSITION_TARGETS:
        return TargetType.POSITION
    if selector in CONTAINER_TARGETS:
        return TargetType.CARD_CONTAINER
    raise ValueError(f"Unknown target selector: {selector}")


@dataclass(frozen=True)
class Target:
    """Concrete target specification for a single effect endpoint."""

    selector: Targets

    @property
    def target_type(self) -> TargetType:
        """Backward-compatible kind field used by existing call sites."""

        return target_kind_for(self.selector)

    @classmethod
    def from_value(cls, value: "Target | Targets | str") -> "Target":
        """Build a Target from legacy value shapes."""

        if isinstance(value, Target):
            return value
        if isinstance(value, Targets):
            return cls(value)
        if isinstance(value, str):
            return cls(Targets(value))
        raise TypeError(f"Unsupported target value: {value!r}")


@dataclass(frozen=True)
class MoveTarget:
    """Target specification for movement and summon effects."""

    source: Target
    destination: Target

    def __post_init__(self) -> None:
        if self.source.target_type != TargetType.CARD:
            raise ValueError("Move or summon source must target cards")
        if self.destination.target_type != TargetType.POSITION:
            raise ValueError("Move or summon destination must target positions")


@dataclass(frozen=True)
class SwapTarget:
    """Target specification for swap and transform effects."""

    first: Target
    second: Target

    def __post_init__(self) -> None:
        if self.first.target_type != self.second.target_type:
            raise ValueError("Swap or transform targets must be of the same type")
        if self.first.target_type == TargetType.CARD_CONTAINER:
            raise ValueError("Swap or transform effects cannot target card containers")


@dataclass(frozen=True)
class CopyTarget:
    """Target specification for copy effects."""

    source: Target
    destination: Target

    def __post_init__(self) -> None:
        if self.source.target_type != TargetType.CARD:
            raise ValueError("Copy source must target a card")
        if self.destination.target_type == TargetType.CARD:
            raise ValueError(
                "Copy destination must target a position or a card container"
            )


class Event(str, Enum):
    """Events for card effect triggering."""

    ON_PLAY = "on_play"
    ON_DRAW = "on_draw"
    ON_DISCARD = "on_discard"

    ON_FIRST_ROUND_START = "on_first_round_start"
    ON_SECOND_ROUND_START = "on_second_round_start"
    ON_THIRD_ROUND_START = "on_third_round_start"
    ON_TURN_START = "on_turn_start"
    ON_TURN_END = "on_turn_end"


@dataclass
class Trigger:
    """Represents a trigger for a card effect."""

    event: Event
    activate_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    deactivate_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: False
    )
    trigger_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    countdown: int = 0
    countdowm_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    repeat: Optional[int] = None
    repeat_interval: Optional[int] = None
    repeat_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    initially_active: bool = True

    def __post_init__(self) -> None:
        if self.countdown < 0:
            raise ValueError("Countdown cannot be negative")
        if self.repeat and self.repeat <= 0:
            raise ValueError("Repeat count must be positive or None")
        if self.repeat_interval and self.repeat_interval <= 0:
            raise ValueError("Repeat interval must be positive or None")

        self.current_countdown = self.countdown
        self.current_repeat_cooldown = 0
        self.current_repeats = 0
        self.is_active = self.initially_active
        self.activated_on: Optional[int] = None
        if self.initially_active:
            self.activated_on = 0
        self.last_repeat_on: Optional[int] = None

    def start_countdown(
        self, event: Event, player: "Player", card: "Card", game: "Game"
    ) -> None:
        """Legacy helper: arm the initial countdown if trigger can become active."""

        if event != self.event:
            return

        if not self.is_active and not self.deactivate_condition(
            event, player, card, game
        ):
            if self.activate_condition(event, player, card, game):
                self.is_active = True
                self.activated_on = game.current_turn
                self.current_countdown = self.countdown

    def update_countdown(
        self, event: Event, player: "Player", card: "Card", game: "Game"
    ) -> None:
        """Legacy helper: step countdown/cooldown on matching events."""

        if event != self.event or not self.is_active:
            return

        if self.current_repeat_cooldown > 0:
            if self.countdowm_condition(event, player, card, game):
                self.current_repeat_cooldown -= 1
            return

        if self.current_countdown > 0 and self.countdowm_condition(
            event, player, card, game
        ):
            self.current_countdown -= 1

    def reset(self) -> None:
        """Reset the trigger state."""

        self.is_active = self.initially_active
        self.activated_on = None
        if self.initially_active:
            self.activated_on = 0
        self.current_countdown = self.countdown
        self.current_repeat_cooldown = 0
        self.current_repeats = 0
        self.last_repeat_on = None

    @property
    def countdown_condition(self) -> Callable[[Event, "Player", "Card", "Game"], bool]:
        """Alias with corrected spelling for compatibility."""

        return self.countdowm_condition

    def should_trigger(
        self, event: Event, player: "Player", card: "Card", game: "Game"
    ) -> bool:
        """Check whether this trigger should fire now.

        This separates two concepts:
        - active state (effect is on/off), controlled by activate/deactivate conditions
        - fire condition (effect triggers now), controlled by trigger_condition
        """

        if event != self.event:
            return False

        if self.is_active:
            if self.deactivate_condition(event, player, card, game):
                self.is_active = False
                self.activated_on = None
                self.current_countdown = self.countdown
                self.current_repeat_cooldown = 0
                return False
        elif not self.deactivate_condition(event, player, card, game):
            if self.activate_condition(event, player, card, game):
                self.is_active = True
                self.activated_on = game.current_turn
                self.current_countdown = self.countdown
                self.current_repeat_cooldown = 0

        if not self.is_active:
            return False

        if self.repeat and self.current_repeats >= self.repeat:
            return False

        if self.current_repeat_cooldown > 0:
            if self.countdowm_condition(event, player, card, game):
                self.current_repeat_cooldown -= 1
            return False

        if self.current_countdown > 0:
            if self.countdowm_condition(event, player, card, game):
                self.current_countdown -= 1
            return False

        if self.current_repeats > 0 and not self.repeat_condition(
            event, player, card, game
        ):
            return False

        if not self.trigger_condition(event, player, card, game):
            return False

        self.current_repeats += 1
        self.last_repeat_on = game.current_turn

        if self.repeat_interval:
            self.current_repeat_cooldown = self.repeat_interval

        return True


def _coerce_single_target(value: Target | Targets | str) -> Target:
    return Target.from_value(value)


@dataclass
class Effect:
    """Represents a card effect."""

    description: str
    effect_type: EffectType
    target_type: (
        Target
        | MoveTarget
        | SwapTarget
        | CopyTarget
        | Targets
        | str
        | tuple[Target | Targets | str, Target | Targets | str]
    )

    trigger_on_event: Event
    trigger_activate_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    trigger_deactivate_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: False
    )
    trigger_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    trigger_countdown: int = 0
    trigger_countdowm_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    trigger_repeat: Optional[int] = None
    trigger_repeat_interval: Optional[int] = None
    trigger_repeat_condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    trigger_initially_active: bool = True

    value: Optional[int | PowerTable] = None

    def __post_init__(self) -> None:
        self.trigger = Trigger(
            event=self.trigger_on_event,
            activate_condition=self.trigger_activate_condition,
            deactivate_condition=self.trigger_deactivate_condition,
            trigger_condition=self.trigger_condition,
            countdown=self.trigger_countdown,
            countdowm_condition=self.trigger_countdowm_condition,
            repeat=self.trigger_repeat,
            repeat_interval=self.trigger_repeat_interval,
            repeat_condition=self.trigger_repeat_condition,
            initially_active=self.trigger_initially_active,
        )

        self.target = self._normalize_target(self.target_type)
        self._validate_effect_shape()

    @property
    def cost(self) -> int:
        """Calculate the cost of the effect based on its type and value."""

        # TODO: Implement a more sophisticated cost calculation based on effect type and value.
        return 0

    def _normalize_target(
        self,
        raw_target: (
            Target
            | MoveTarget
            | SwapTarget
            | CopyTarget
            | Targets
            | str
            | tuple[Target | Targets | str, Target | Targets | str]
        ),
    ) -> Target | MoveTarget | SwapTarget | CopyTarget:
        if isinstance(raw_target, (MoveTarget, SwapTarget, CopyTarget)):
            return raw_target

        elif isinstance(raw_target, tuple):
            if len(raw_target) != 2:
                raise ValueError(
                    "Move, Swap, or Copy target must be a tuple of two target values"
                )

            match self.effect_type:
                case EffectType.MOVE | EffectType.SUMMON:
                    source = _coerce_single_target(raw_target[0])
                    destination = _coerce_single_target(raw_target[1])
                    return MoveTarget(source=source, destination=destination)
                case (
                    EffectType.SWAP_POWER
                    | EffectType.SWAP_POSITION
                    | EffectType.TRANSFORM
                ):
                    first = _coerce_single_target(raw_target[0])
                    second = _coerce_single_target(raw_target[1])
                    return SwapTarget(first=first, second=second)
                case EffectType.COPY:
                    source = _coerce_single_target(raw_target[0])
                    destination = _coerce_single_target(raw_target[1])
                    return CopyTarget(source=source, destination=destination)
                case _:
                    raise ValueError(
                        "Only Move, Swap, Transform, and Copy effects can have tuple targets"
                    )

        else:
            return _coerce_single_target(raw_target)

    def _validate_effect_shape(self) -> None:
        if self.effect_type in {
            EffectType.BUFF,
            EffectType.MULTIPLY_POWER,
            EffectType.SET_POWER,
        }:
            if not self.value:
                raise ValueError("Value must be provided for power effects")
            if isinstance(self.target, (MoveTarget, SwapTarget, CopyTarget)):
                raise ValueError("Power effects require a single target")
            if self.target.target_type != TargetType.CARD:
                raise ValueError("Power effects must target cards")

        elif self.effect_type in {
            EffectType.DESTROY,
            EffectType.SHIELD,
            EffectType.IMMUNITY,
            EffectType.CLEANSE,
            EffectType.DRAW,
            EffectType.DISCARD,
            EffectType.SILENCE,
            EffectType.CANCEL,
        }:
            if self.value:
                raise ValueError("Value cannot be provided for these effects")
            if isinstance(self.target, (MoveTarget, SwapTarget, CopyTarget)):
                raise ValueError("These effects require a single target")

        elif self.effect_type in {
            EffectType.LOCK_POSITION,
            EffectType.UNLOCK_POSITION,
        }:
            if self.value:
                raise ValueError(
                    "Value cannot be provided for summon or position effects"
                )
            if isinstance(self.target, (MoveTarget, SwapTarget, CopyTarget)):
                raise ValueError("Lock/unlock effects require a single target")
            if self.target.target_type != TargetType.POSITION:
                raise ValueError("Lock/unlock effects must target positions")

        elif self.effect_type in {EffectType.MOVE, EffectType.SUMMON}:
            if self.value:
                raise ValueError("Value cannot be provided for move or summon effects")
            if not isinstance(self.target, MoveTarget):
                raise ValueError(
                    "Move or summon effects require a source and destination target"
                )

        elif self.effect_type in {
            EffectType.SWAP_POWER,
            EffectType.SWAP_POSITION,
            EffectType.TRANSFORM,
        }:
            if self.value:
                raise ValueError(
                    "Value cannot be provided for swap or transform effects"
                )
            if not isinstance(self.target, SwapTarget):
                raise ValueError(
                    "Swap or transform effects require two targets to swap or transform between"
                )

        elif self.effect_type == EffectType.COPY:
            if self.value:
                raise ValueError("Value cannot be provided for copy effects")
            if not isinstance(self.target, CopyTarget):
                raise ValueError("Copy effects require a source and destination target")

        else:
            raise ValueError(f"Unknown effect type: {self.effect_type}")
