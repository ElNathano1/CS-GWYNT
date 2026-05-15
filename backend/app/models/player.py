"""Player Model"""

import random

from dataclasses import dataclass, field
from typing import List, Dict
from .card import Card


@dataclass
class Player:
    """Represents a player in the game"""

    id: int
    username: str
    hand: List[Card] = field(default_factory=list)
    deck: List[Card] = field(default_factory=list)
    discard_pile: List[Card] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the player's terrain and other attributes"""

        self.terrain: Dict[str, List[Card]] = {}
        self._shuffle_deck()

    def _shuffle_deck(self) -> None:
        """Shuffle the player's deck"""

        random.shuffle(self.deck)

    def draw_card(self) -> Card:
        """Draw a card from the deck"""

        try:
            return self.deck.pop(0)

        except IndexError:
            raise Exception("Deck is empty")

    def play_card(self, card: Card, lane: Lane) -> None:
        """Play a card from the hand"""

        try:
            self.hand.remove(card)
            self.terrain[lane.value].append(card)

        except ValueError:
            raise Exception("Card not in hand")

    def discard_card(self, card: Card) -> None:
        """Discard a card from the hand"""

        try:
            self.hand.remove(card)
            self.discard_pile.append(card)

        except ValueError:
            raise Exception("Card not in hand")
