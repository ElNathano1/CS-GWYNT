"""Card Model"""

from enum import Enum
from typing import Optional
from .basic_classes import *

import os
from dotenv import load_dotenv

load_dotenv()

RARITY_BUDGET = os.getenv("RARITY_BUDGET")


class CardRarity(Enum):
    """Card rarity levels"""

    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Card:
    """Represents a trading card"""

    id: int
    name: str
    description: str
    rarity: CardRarity
    cost: int
    power_table: Power | tuple[int, int, int]

    def __post_init__(self):
        if isinstance(self.power_table, tuple):
            self.power_table = Power(*self.power_table)

        self.budget = RARITY_BUDGET.get(self.rarity.value, 0)
