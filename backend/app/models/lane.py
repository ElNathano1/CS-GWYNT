"""Lane, Hand, Deck, and Discard Models"""

from enum import Enum
import random

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .card import Card
from .effect import Effect

import os
from dotenv import load_dotenv
import json

load_dotenv()


class LaneType(Enum):
    """Types of lane where to place a card"""

    FRONTSTAGE = "frontstage"
    OFFSTAGE = "offstage"
    BACKSTAGE = "backstage"


@dataclass
class Lane(List[Card]):
    """Represents a lane where cards can be placed"""

    type: LaneType
    max_len: int = int(os.getenv("LANE_SIZE", 5))
    effect: Optional[Effect] = None

    def __post_init__(self):
        if len(self) > self.max_len:
            raise ValueError(f"Lane cannot have more than {self.max_len} cards")

        self.current_power = self.update_power()

    def update_power(self) -> int:
        """Calculate the total power of the lane"""

        return sum(card.current_power for card in self)

    def append(self, card: Card) -> None:
        """Add a card to the lane"""

        if len(self) >= self.max_len:
            raise IndexError("Lane is full")

        super().append(card)
        card.current_lane = self.type
        card.current_power = card.power_table.__getattribute__(self.type.value)
        self.current_power = self.update_power()

    def remove(self, card: Card) -> None:
        """Remove a card from the lane"""

        try:
            super().remove(card)

        except ValueError:
            raise IndexError("Card not in lane")

        card.current_lane = None
        card.current_power = 0
        self.current_power = self.update_power()


@dataclass
class Hand(List[Card]):
    """Represents a player's hand"""

    max_len: int = int(os.getenv("MAX_HAND_SIZE", 10))

    def __post_init__(self):
        if len(self) > self.max_len:
            raise ValueError(f"Hand cannot have more than {self.max_len} cards")

    def append(self, card: Card) -> None:
        """Add a card to the hand"""

        if len(self) >= self.max_len:
            raise IndexError("Hand is full")

        super().append(card)

    def remove(self, card: Card) -> None:
        """Remove a card from the hand"""

        try:
            super().remove(card)

        except ValueError:
            raise IndexError("Card not in hand")


@dataclass
class Pile(List[Card]):
    """Represents a pile of cards (deck or discard)"""

    max_len: int | None = int(os.getenv("MAX_DECK_SIZE", 30))

    def __post_init__(self):
        if self.max_len and len(self) > self.max_len:
            raise ValueError(f"This pile cannot have more than {self.max_len} cards")

    def copy(self) -> "Pile":
        """Return a copy of the pile"""

        return Pile(super(), max_len=self.max_len)  # type: ignore

    def append(self, card: Card) -> None:
        """Add a card to the pile"""

        if self.max_len and len(self) >= self.max_len:
            raise IndexError("Pile is full")

        super().append(card)

    def insert(self, card: Card, index: int | None = None) -> None:
        """Insert a card at a specific position in the pile. If index is None, the card will be added to a random position"""

        if self.max_len and len(self) >= self.max_len:
            raise IndexError("Pile is full")

        if index is None:
            index = random.randint(0, len(self))

        super().insert(index, card)

    def remove(self, card: Card) -> None:
        """Remove a card from the pile"""

        try:
            super().remove(card)

        except ValueError:
            raise IndexError("Card not in pile")

    def shuffle(self) -> None:
        """Shuffle the pile"""

        random.shuffle(self)

    def draw(self) -> Card:
        """Draw a card from the pile"""

        try:
            return self.pop(0)

        except IndexError:
            raise IndexError("Pile is empty")

    def show(self, shuffle: bool = False) -> List[Dict]:
        """Return a list of card details in the pile"""

        presentation = self.copy()

        if shuffle:
            presentation.shuffle()

        return [
            {
                "id": card.id,
                "name": card.name,
                "description": card.description,
                "rarity": card.rarity.value,
                "power_table": {
                    "frontstage": card.power_table.frontstage,  # type: ignore
                    "offstage": card.power_table.offstage,  # type: ignore
                    "backstage": card.power_table.backstage,  # type: ignore
                },
                "effect": (
                    card.effect.to_dict()
                    if card.effect
                    else None
                ),
            }
            for card in presentation
        ]
