"""Basic Classes for CS-Gwynt Game"""

import statistics

from dataclasses import dataclass
from enum import Enum
import os
from dotenv import load_dotenv
import json

from .card import Card

load_dotenv()


def load_dict_from_env(key: str, default: dict = {}) -> dict:
    """Load a dictionary from environment variable"""
    return json.loads(os.getenv(key, json.dumps(default)))


def cost_function(card: "Card") -> int:
    """Calculate the cost of a card based on its attributes"""

    sum = card.power_table.sum()  # type: ignore
    std = card.power_table.std()  # type: ignore

    return max(0, round(sum - 9 * ((std / card.budget) ** 2) + card.effect.cost))


class Lane(Enum):
    """Lane where to place a card"""

    FRONTSTAGE = "frontstage"
    OFFSTAGE = "offstage"
    BACKSTAGE = "backstage"


@dataclass
class PowerTable:
    """Represents the power of a card"""

    frontstage: int = 0
    offstage: int = 0
    backstage: int = 0

    def __post_init__(self):
        if not all(
            isinstance(x, int) and x >= 0
            for x in [self.frontstage, self.offstage, self.backstage]
        ):
            raise ValueError("Power values must be non-negative integers")

    def sum(self):
        return self.frontstage + self.offstage + self.backstage

    def std(self):
        return statistics.stdev([self.frontstage, self.offstage, self.backstage])
