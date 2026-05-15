"""Card Model"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Tuple
from .utils import PowerTable

import os
from dotenv import load_dotenv
import json

load_dotenv()

RARITY_BUDGET: Dict[str, int] = json.loads(os.getenv("RARITY_BUDGET", "{}"))


class EffectType(str, Enum):
    """Types of card effects"""

    pass


@dataclass
class Effect:
    """Represents a card effect"""

    pass


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
    power_table: PowerTable | Tuple[int, int, int]

    def __post_init__(self):
        if isinstance(self.power_table, Tuple):
            self.power_table = PowerTable(*self.power_table)

        self.budget = RARITY_BUDGET.get(self.rarity.value, 0)
