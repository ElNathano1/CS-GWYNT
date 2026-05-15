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

    def append(self, card: Card) -> None:
        """Add a card to the lane"""

        if len(self) >= self.max_len:
            raise IndexError("Lane is full")

        super().append(card)
        card.current_lane = self.type
        card.current_power = card.power_table.__getattribute__(self.type.value)

    def remove(self, card: Card) -> None:
        """Remove a card from the lane"""

        try:
            super().remove(card)

        except ValueError:
            raise IndexError("Card not in lane")

        card.current_lane = None
        card.current_power = 0

    def current_power(self) -> int:
        """Calculate the total power of the lane"""

        return sum(card.current_power for card in self)
