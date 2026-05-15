"""Basic Classes for CS-Gwynt Game"""

import statistics

from dataclasses import dataclass
from enum import Enum
import os
from typing import TYPE_CHECKING
from dotenv import load_dotenv
import json

if TYPE_CHECKING:
    from .card import Card

load_dotenv()


def load_dict_from_env(key: str, default: dict = {}) -> dict:
    """Load a dictionary from environment variable"""
    return json.loads(os.getenv(key, json.dumps(default)))


def cost_function(card: "Card") -> int:
    """Calculate the cost of a card based on its attributes"""

    sum = card.power_table.sum()  # type: ignore
    std = card.power_table.std()  # type: ignore

    if card.effect:
        sum += card.effect.cost

    return max(0, round(sum - 9 * ((std / card.budget) ** 2)))


@dataclass
class PowerTable:
    """Represents the power of a card"""

    frontstage: int = 0
    offstage: int = 0
    backstage: int = 0

    def sum(self):
        return self.frontstage + self.offstage + self.backstage

    def std(self):
        return statistics.stdev([self.frontstage, self.offstage, self.backstage])

    def __neg__(self) -> "PowerTable":
        return PowerTable(
            frontstage=-self.frontstage,
            offstage=-self.offstage,
            backstage=-self.backstage,
        )

    def __add__(self, other: "PowerTable") -> "PowerTable":
        return PowerTable(
            frontstage=self.frontstage + other.frontstage,
            offstage=self.offstage + other.offstage,
            backstage=self.backstage + other.backstage,
        )

    def __sub__(self, other: "PowerTable") -> "PowerTable":
        return PowerTable(
            frontstage=self.frontstage - other.frontstage,
            offstage=self.offstage - other.offstage,
            backstage=self.backstage - other.backstage,
        )

    def __mul__(self, other: "int | PowerTable") -> "PowerTable":
        if isinstance(other, int):
            return PowerTable(
                frontstage=self.frontstage * other,
                offstage=self.offstage * other,
                backstage=self.backstage * other,
            )
        elif isinstance(other, PowerTable):
            return PowerTable(
                frontstage=self.frontstage * other.frontstage,
                offstage=self.offstage * other.offstage,
                backstage=self.backstage * other.backstage,
            )
        else:
            raise TypeError(
                "Unsupported operand type(s) for *: 'PowerTable' and '{}'".format(
                    type(other).__name__
                )
            )
