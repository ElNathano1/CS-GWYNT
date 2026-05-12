"""Player Model"""

from typing import List
from .card import Card


class Player:
    """Represents a player in the game"""

    def __init__(self, id: int, username: str, deck: List[Card] = None):
        self.id = id
        self.username = username
        self.hand: List[Card] = []
        self.deck: List[Card] = deck or []
        self.discard_pile: List[Card] = []

    def draw_card(self) -> Card:
        """Draw a card from the deck"""
        if self.deck:
            return self.deck.pop(0)
        return None

    def play_card(self, card: Card) -> bool:
        """Play a card from the hand"""
        if card in self.hand:
            self.hand.remove(card)
            self.discard_pile.append(card)
            return True
        return False

    def __repr__(self) -> str:
        return f"Player(id={self.id}, username='{self.username}', health={self.health})"
