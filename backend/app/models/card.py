"""Card Model"""

from enum import Enum
from typing import Optional
from .utils import *

import os
from dotenv import load_dotenv
import json

load_dotenv()

RARITY_BUDGET: dict[str, int] = json.loads(os.getenv("RARITY_BUDGET", "{}"))


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
    power_table: PowerTable | tuple[int, int, int]

    def __post_init__(self):
        if isinstance(self.power_table, tuple):
            self.power_table = PowerTable(*self.power_table)

        self.budget = RARITY_BUDGET.get(self.rarity.value, 0)
