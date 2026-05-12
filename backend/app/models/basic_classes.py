"""Basic Classes for CS-Gwynt Game"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Location(Enum):
    """Location where to place a card"""

    FRONTSTAGE = "frontstage"
    OFFSTAGE = "offstage"
    BACKSTAGE = "backstage"


@dataclass
class Power:
    """Represents the power of a card"""

    frontstage: int = 0
    offstage: int = 0
    backstage: int = 0


class EffectType(str, Enum):
    """Types of card effects"""

    pass


class Effect:
    """Represents a card effect"""

    pass
