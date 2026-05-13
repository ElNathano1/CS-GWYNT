"""Effect Model"""

import random

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, List

from .utils import Lane
from .card import Card
from .player import Player
from .game import Game


class EffectType(str, Enum):
    """Types of card effects"""

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


class TargetType(str, Enum):
    """Targets for card effects"""

    SELF = "self"
    CARD = "card"
    RANDOM_CARD = "random_card"

    ALLY = "ally"
    ENEMY = "enemy"
    RANDOM_ALLY = "random_ally"
    RANDOM_ENEMY = "random_enemy"

    ALL_ALLIES = "all_allies"
    ALL_ENEMIES = "all_enemies"
    ALL_OTHER_ALLIES = "all_other_allies"
    ALL_OTHER_ENEMIES = "all_other_enemies"
    ALL_OTHER_CARDS = "all_other_cards"
    ALL_CARDS = "all_cards"

    ADJACENT = "adjacent"
    LANE = "lane"
    RANDOM_LANE = "random_lane"

    ALLY_LANE = "ally_lane"
    ENEMY_LANE = "enemy_lane"
    RANDOM_ALLY_LANE = "random_ally_lane"
    RANDOM_ENEMY_LANE = "random_enemy_lane"

    ALL_ALLY_LANES = "all_ally_lanes"
    ALL_ENEMY_LANES = "all_enemy_lanes"
    ALL_OTHER_ALLY_LANES = "all_other_ally_lanes"
    ALL_OTHER_ENEMY_LANES = "all_other_enemy_lanes"
    ALL_OTHER_LANES = "all_other_lanes"
    ALL_BOARD = "all_board"

    HAND = "hand"
    ENEMY_HAND = "enemy_hand"
    DECK = "deck"
    ENEMY_DECK = "enemy_deck"
    DISCARD = "discard"
    ENEMY_DISCARD = "enemy_discard"


class Event(str, Enum):
    """Events for card effects triggering"""

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
    """Represents a trigger for a card effect"""

    event: Event
    condition: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    countdown: int = 0
    condition_countdown: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )
    repeat: Optional[int] = None
    repeat_interval: Optional[int] = None
    condition_repeat: Callable[[Event, "Player", "Card", "Game"], bool] = (
        lambda event, player, card, game: True
    )

    def __post_init__(self):
        if self.countdown < 0:
            raise ValueError("Countdown cannot be negative")
        if self.repeat and self.repeat <= 0:
            raise ValueError("Repeat count must be positive or None")
        if self.repeat_interval and self.repeat_interval <= 0:
            raise ValueError("Repeat interval must be positive or None")

        self.current_countdown = self.countdown
        self.current_repeats = 0
        self.start_countdown_on: Optional[int] = None
        self.last_repeat_on: Optional[int] = None
        self.triggered_on: Optional[int] = None

    def start_countdown(
        self, event: Event, player: "Player", card: "Card", game: "Game"
    ) -> None:
        """Start the countdown for the trigger"""

        if (
            not self.start_countdown_on
            and event == self.event
            and self.condition(event, player, card, game)
        ):
            self.start_countdown_on = game.current_turn

    def update_countdown(
        self, event: Event, player: "Player", card: "Card", game: "Game"
    ) -> None:
        """Update the countdown for the trigger"""

        if (
            self.start_countdown_on
            and self.current_countdown > 0
            and self.start_countdown_on < game.current_turn
            and self.condition_countdown(event, player, card, game)
        ):
            self.current_countdown -= 1

    def reset(self) -> None:
        """Reset the trigger state"""

        self.start_countdown_on = None
        self.current_countdown = self.countdown
        self.current_repeats = 0
        self.triggered_on = None

    def should_trigger(
        self, event: Event, player: "Player", card: "Card", game: "Game"
    ) -> bool:
        """Check if the trigger should activate based on the event and conditions"""

        if self.repeat and self.current_repeats >= self.repeat:
            return False

        if (
            self.repeat
            and self.current_repeats < self.repeat
            and self.condition_repeat(event, player, card, game)
            and (
                not self.repeat_interval
                or not self.last_repeat_on
                or game.current_turn >= self.last_repeat_on + self.repeat_interval
            )
        ):
            self.current_repeats += 1
            self.last_repeat_on = game.current_turn

            return True

        if self.event != event:
            return False

        if self.current_countdown > 0:
            return False

        if self.delay > 0:
            if self.triggered_on is None:
                self.triggered_on = game.current_turn + self.delay
                return False
            elif game.current_turn < self.triggered_on:
                return False

        if self.countdown is not None:
            if self.triggered_on is None:
                self.triggered_on = game.current_turn
            elif game.current_turn >= self.triggered_on + self.countdown:
                return False

        if self.repeat is not None:
            if self.triggered_on is None:
                self.triggered_on = game.current_turn
            elif game.current_turn >= self.triggered_on + (
                self.repeat * (self.countdown or 1)
            ):
                return False

        return self.condition(event, player, card, game)


class Effect:
    """Represents a card effect"""

    pass
