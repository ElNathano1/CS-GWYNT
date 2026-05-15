"""Card Model"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Tuple
from .effect import Effect
from .power import PowerTable, cost_function
from .lane import LaneType

import os
from dotenv import load_dotenv
import json

load_dotenv()

RARITY_BUDGET: Dict[str, int] = json.loads(os.getenv("RARITY_BUDGET", "{}"))


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

    effect: Optional[Effect] = None  # type: ignore

    current_lane: Optional[LaneType] = None

    def __post_init__(self):
        if isinstance(self.power_table, Tuple):
            self.power_table = PowerTable(*self.power_table)

        if not all(
            isinstance(x, int) and x >= 0
            for x in [
                self.power_table.frontstage,
                self.power_table.offstage,
                self.power_table.backstage,
            ]
        ):
            raise ValueError("Power values must be non-negative integers")

        self.current_power = self.power_table.__getattribute__(self.current_lane.value) if self.current_lane else 0  # type: ignore

        self.budget = RARITY_BUDGET.get(self.rarity.value, 0)

        if cost_function(self) > self.budget:
            raise ValueError(
                f"Card cost {cost_function(self)} exceeds budget of {self.budget} for rarity {self.rarity.value}"
            )
