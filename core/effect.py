"""Effect model."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

from .power import PowerTable

if TYPE_CHECKING:
    from .card import Card
    from .game import Game
    from .player import Player


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
    RANDOM_CARD_ON_LANE = "random_card_on_lane"

    # Single card targets with constraints of both player and position
    RANDOM_CARD_ON_ALLY_LANE = "random_card_on_ally_lane"
    RANDOM_CARD_ON_ENEMY_LANE = "random_card_on_enemy_lane"

    # Multiple card targets with constraints of both player and position
    ALL_CARDS_ON_OTHER_ALLY_LANES = "all_other_ally_lanes"
    ALL_CARDS_ON_OTHER_ENEMY_LANES = "all_other_enemy_lanes"
    ALL_CARDS_ON_OTHER_LANES = "all_other_lanes"

    # Single card targets with constraints of container
    CARD_IN_HAND = "card_in_hand"
    CARD_IN_ENEMY_HAND = "card_in_enemy_hand"
    RANDOM_CARD_IN_HAND = "random_card_in_hand"
    RANDOM_CARD_IN_ENEMY_HAND = "random_card_in_enemy_hand"
    RANDOM_CARD_IN_HANDS = "random_card_in_hands"

    CARD_IN_DECK = "card_in_deck"
    CARD_IN_ENEMY_DECK = "card_in_enemy_deck"
    NEXT_CARD_IN_DECK = "next_card_in_deck"
    NEXT_CARD_IN_ENEMY_DECK = "next_card_in_enemy_deck"
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
    Targets.RANDOM_CARD_ON_LANE,
    Targets.RANDOM_CARD_ON_ALLY_LANE,
    Targets.RANDOM_CARD_ON_ENEMY_LANE,
    Targets.ALL_CARDS_ON_OTHER_ALLY_LANES,
    Targets.ALL_CARDS_ON_OTHER_ENEMY_LANES,
    Targets.ALL_CARDS_ON_OTHER_LANES,
    Targets.CARD_IN_HAND,
    Targets.CARD_IN_ENEMY_HAND,
    Targets.RANDOM_CARD_IN_HAND,
    Targets.RANDOM_CARD_IN_ENEMY_HAND,
    Targets.RANDOM_CARD_IN_HANDS,
    Targets.CARD_IN_DECK,
    Targets.CARD_IN_ENEMY_DECK,
    Targets.NEXT_CARD_IN_DECK,
    Targets.NEXT_CARD_IN_ENEMY_DECK,
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


class ConditionOperator(str, Enum):
    """Operators used by declarative trigger conditions."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NIN = "nin"


class ConditionLogic(str, Enum):
    """How to combine multiple conditions."""

    ALL = "all"
    ANY = "any"


ConditionValue = int | float | str | bool


@dataclass(frozen=True)
class Condition:
    """Declarative condition usable for activation/deactivation/trigger checks."""

    field_name: str
    operator: ConditionOperator
    value: ConditionValue | list[ConditionValue]

    def evaluate(
        self, metrics: dict[str, ConditionValue | list[ConditionValue]]
    ) -> bool:
        left = metrics.get(self.field_name)
        right = self.value

        if self.operator == ConditionOperator.EQ:
            return left == right
        if self.operator == ConditionOperator.NE:
            return left != right
        if left is None:
            return False
        if self.operator == ConditionOperator.GT:
            return left > right  # type: ignore[operator]
        if self.operator == ConditionOperator.GTE:
            return left >= right  # type: ignore[operator]
        if self.operator == ConditionOperator.LT:
            return left < right  # type: ignore[operator]
        if self.operator == ConditionOperator.LTE:
            return left <= right  # type: ignore[operator]
        if self.operator == ConditionOperator.IN:
            if not isinstance(right, list):
                raise ValueError("IN operator requires list value")
            return left in right
        if self.operator == ConditionOperator.NIN:
            if not isinstance(right, list):
                raise ValueError("NIN operator requires list value")
            return left not in right
        raise ValueError(f"Unsupported condition operator: {self.operator}")

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "operator": self.operator.value,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Condition":
        return cls(
            field_name=str(data["field_name"]),
            operator=ConditionOperator(str(data["operator"])),
            value=data.get("value"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class ConditionSet:
    """A list of declarative conditions with ALL/ANY logic."""

    logic: ConditionLogic = ConditionLogic.ALL
    conditions: list[Condition] = field(default_factory=list)

    def evaluate(
        self, metrics: dict[str, ConditionValue | list[ConditionValue]]
    ) -> bool:
        if not self.conditions:
            return True
        if self.logic == ConditionLogic.ALL:
            return all(condition.evaluate(metrics) for condition in self.conditions)
        return any(condition.evaluate(metrics) for condition in self.conditions)

    def to_dict(self) -> dict[str, object]:
        return {
            "logic": self.logic.value,
            "conditions": [condition.to_dict() for condition in self.conditions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ConditionSet":
        raw_conditions = data.get("conditions", [])
        if not isinstance(raw_conditions, list):
            raise ValueError("conditions must be a list")
        return cls(
            logic=ConditionLogic(str(data.get("logic", ConditionLogic.ALL.value))),
            conditions=[
                Condition.from_dict(item)
                for item in raw_conditions
                if isinstance(item, dict)
            ],
        )


@dataclass
class Trigger:
    """Declarative trigger state machine, serializable for database storage."""

    event: Event
    activate_when: Optional[ConditionSet] = None
    deactivate_when: Optional[ConditionSet] = None
    fire_when: Optional[ConditionSet] = None
    countdown: int = 0
    repeat_limit: Optional[int] = None
    repeat_interval: int = 0
    initially_active: bool = True

    def __post_init__(self) -> None:
        if self.countdown < 0:
            raise ValueError("Countdown cannot be negative")
        if self.repeat_limit and self.repeat_limit <= 0:
            raise ValueError("Repeat count must be positive or None")
        if self.repeat_interval < 0:
            raise ValueError("Repeat interval must be non-negative")

        self._remaining_countdown = self.countdown
        self._remaining_cooldown = 0
        self._trigger_count = 0
        self._is_active = self.initially_active
        self._activated_on_turn: Optional[int] = None
        self._last_trigger_turn: Optional[int] = None

    def reset(self) -> None:
        """Reset the trigger state."""

        self._remaining_countdown = self.countdown
        self._remaining_cooldown = 0
        self._trigger_count = 0
        self._is_active = self.initially_active
        self._activated_on_turn = None
        self._last_trigger_turn = None

    def to_dict(self, include_runtime_state: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "event": self.event.value,
            "activate_when": (
                self.activate_when.to_dict() if self.activate_when else None
            ),
            "deactivate_when": (
                self.deactivate_when.to_dict() if self.deactivate_when else None
            ),
            "fire_when": self.fire_when.to_dict() if self.fire_when else None,
            "countdown": self.countdown,
            "repeat_limit": self.repeat_limit,
            "repeat_interval": self.repeat_interval,
            "initially_active": self.initially_active,
        }
        if include_runtime_state:
            payload["runtime_state"] = {
                "remaining_countdown": self._remaining_countdown,
                "remaining_cooldown": self._remaining_cooldown,
                "trigger_count": self._trigger_count,
                "is_active": self._is_active,
                "activated_on_turn": self._activated_on_turn,
                "last_trigger_turn": self._last_trigger_turn,
            }
        return payload

    @staticmethod
    def _safe_int(value: object, default: int = 0) -> int:
        if isinstance(value, (int, float, str, bool)):
            return int(value)
        return default

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Trigger":
        activate_payload = data.get("activate_when")
        deactivate_payload = data.get("deactivate_when")
        fire_payload = data.get("fire_when")
        repeat_limit_raw = data.get("repeat_limit")

        trigger = cls(
            event=Event(str(data["event"])),
            activate_when=(
                ConditionSet.from_dict(activate_payload)
                if isinstance(activate_payload, dict)
                else None
            ),
            deactivate_when=(
                ConditionSet.from_dict(deactivate_payload)
                if isinstance(deactivate_payload, dict)
                else None
            ),
            fire_when=(
                ConditionSet.from_dict(fire_payload)
                if isinstance(fire_payload, dict)
                else None
            ),
            countdown=Trigger._safe_int(data.get("countdown", 0)),
            repeat_limit=(
                Trigger._safe_int(repeat_limit_raw)
                if repeat_limit_raw is not None
                else None
            ),
            repeat_interval=Trigger._safe_int(data.get("repeat_interval", 0)),
            initially_active=bool(data.get("initially_active", True)),
        )

        runtime_state = data.get("runtime_state")
        if isinstance(runtime_state, dict):
            trigger._remaining_countdown = int(
                runtime_state.get("remaining_countdown", trigger.countdown)
            )
            trigger._remaining_cooldown = int(
                runtime_state.get("remaining_cooldown", 0)
            )
            trigger._trigger_count = int(runtime_state.get("trigger_count", 0))
            trigger._is_active = bool(
                runtime_state.get("is_active", trigger.initially_active)
            )
            trigger._activated_on_turn = (
                int(runtime_state["activated_on_turn"])
                if runtime_state.get("activated_on_turn") is not None
                else None
            )
            trigger._last_trigger_turn = (
                int(runtime_state["last_trigger_turn"])
                if runtime_state.get("last_trigger_turn") is not None
                else None
            )

        return trigger

    def _build_metrics(
        self,
        player: "Player",
        card: "Card",
        game: "Game",
        extra_metrics: Optional[dict[str, ConditionValue | list[ConditionValue]]],
    ) -> dict[str, ConditionValue | list[ConditionValue]]:
        metrics: dict[str, ConditionValue | list[ConditionValue]] = {
            "current_turn": int(getattr(game, "current_turn", 0)),
        }

        player_board = getattr(player, "board", None)
        if player_board is not None and hasattr(player_board, "cards"):
            player_cards = player_board.cards()  # type: ignore[operator]
            if isinstance(player_cards, list):
                metrics["player_board_count"] = len(player_cards)

        game_board = getattr(game, "board", None)
        if game_board is not None and hasattr(game_board, "cards"):
            game_cards = game_board.cards()  # type: ignore[operator]
            if isinstance(game_cards, list):
                metrics["board_count"] = len(game_cards)

        hand = getattr(player, "hand", None)
        if isinstance(hand, list):
            metrics["player_hand_count"] = len(hand)

        deck = getattr(player, "deck", None)
        if isinstance(deck, list):
            metrics["player_deck_count"] = len(deck)

        discard = getattr(player, "discard", None)
        if isinstance(discard, list):
            metrics["player_discard_count"] = len(discard)

        if extra_metrics:
            metrics.update(extra_metrics)

        return metrics

    def should_trigger(
        self,
        event: Event,
        player: "Player",
        card: "Card",
        game: "Game",
        extra_metrics: Optional[
            dict[str, ConditionValue | list[ConditionValue]]
        ] = None,
    ) -> bool:
        """Check whether this trigger should fire now."""

        if event != self.event:
            return False

        metrics = self._build_metrics(player, card, game, extra_metrics)

        if self._is_active:
            if self.deactivate_when and self.deactivate_when.evaluate(metrics):
                self._is_active = False
                self._activated_on_turn = None
                self._remaining_countdown = self.countdown
                self._remaining_cooldown = 0
                return False
        else:
            if self.deactivate_when and self.deactivate_when.evaluate(metrics):
                return False
            if self.activate_when is None or self.activate_when.evaluate(metrics):
                self._is_active = True
                self._activated_on_turn = int(getattr(game, "current_turn", 0))
                self._remaining_countdown = self.countdown
                self._remaining_cooldown = 0

        if not self._is_active:
            return False

        if self.repeat_limit and self._trigger_count >= self.repeat_limit:
            return False

        if self._remaining_cooldown > 0:
            self._remaining_cooldown -= 1
            return False

        if self._remaining_countdown > 0:
            self._remaining_countdown -= 1
            return False

        if self.fire_when and not self.fire_when.evaluate(metrics):
            return False

        self._trigger_count += 1
        self._last_trigger_turn = int(getattr(game, "current_turn", 0))

        if self.repeat_interval:
            self._remaining_cooldown = self.repeat_interval

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

    trigger: Trigger

    value: Optional[int | PowerTable] = None

    def __post_init__(self) -> None:
        self.target = self._normalize_target(self.target_type)
        self._validate_effect_shape()

    def to_dict(self, include_trigger_runtime_state: bool = False) -> dict[str, object]:
        return {
            "description": self.description,
            "effect_type": self.effect_type.value,
            "target": _serialize_effect_target(self.target),
            "trigger": self.trigger.to_dict(
                include_runtime_state=include_trigger_runtime_state
            ),
            "value": _serialize_effect_value(self.value),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Effect":
        raw_target = data.get("target")
        if not isinstance(raw_target, dict):
            raise ValueError("Effect target payload must be a dict")

        raw_trigger = data.get("trigger")
        if not isinstance(raw_trigger, dict):
            raise ValueError("Effect trigger payload must be a dict")

        return cls(
            description=str(data.get("description", "")),
            effect_type=EffectType(str(data["effect_type"])),
            target_type=_deserialize_effect_target(raw_target),
            trigger=Trigger.from_dict(raw_trigger),
            value=_deserialize_effect_value(data.get("value")),
        )

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


def _serialize_effect_target(
    target: Target | MoveTarget | SwapTarget | CopyTarget,
) -> dict[str, object]:
    if isinstance(target, Target):
        return {
            "shape": "single",
            "selector": target.selector.value,
        }
    if isinstance(target, MoveTarget):
        return {
            "shape": "move",
            "source": target.source.selector.value,
            "destination": target.destination.selector.value,
        }
    if isinstance(target, SwapTarget):
        return {
            "shape": "swap",
            "first": target.first.selector.value,
            "second": target.second.selector.value,
        }
    if isinstance(target, CopyTarget):
        return {
            "shape": "copy",
            "source": target.source.selector.value,
            "destination": target.destination.selector.value,
        }
    raise TypeError(f"Unsupported target type for serialization: {type(target)}")


def _deserialize_effect_target(
    data: dict[str, object],
) -> Target | MoveTarget | SwapTarget | CopyTarget:
    shape = str(data.get("shape", "single"))

    if shape == "single":
        return Target.from_value(str(data["selector"]))
    if shape == "move":
        return MoveTarget(
            source=Target.from_value(str(data["source"])),
            destination=Target.from_value(str(data["destination"])),
        )
    if shape == "swap":
        return SwapTarget(
            first=Target.from_value(str(data["first"])),
            second=Target.from_value(str(data["second"])),
        )
    if shape == "copy":
        return CopyTarget(
            source=Target.from_value(str(data["source"])),
            destination=Target.from_value(str(data["destination"])),
        )
    raise ValueError(f"Unknown target serialization shape: {shape}")


def _serialize_effect_value(
    value: Optional[int | PowerTable],
) -> Optional[dict[str, object]]:
    if value is None:
        return None
    if isinstance(value, int):
        return {
            "type": "int",
            "value": value,
        }
    if isinstance(value, PowerTable):
        return {
            "type": "power_table",
            "frontstage": value.frontstage,
            "offstage": value.offstage,
            "backstage": value.backstage,
        }
    raise TypeError(f"Unsupported effect value type: {type(value)}")


def _deserialize_effect_value(data: object) -> Optional[int | PowerTable]:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Effect value payload must be a dict or None")

    value_type = str(data.get("type", ""))
    if value_type == "int":
        return int(data["value"])
    if value_type == "power_table":
        return PowerTable(
            frontstage=int(data.get("frontstage", 0)),
            offstage=int(data.get("offstage", 0)),
            backstage=int(data.get("backstage", 0)),
        )
    raise ValueError(f"Unknown effect value type: {value_type}")
