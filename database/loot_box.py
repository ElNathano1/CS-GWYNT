"""
DTO for the LootBox database entity.

LootBoxDTO is a plain Python object (no SQLAlchemy dependency) used to transfer
loot box data between the database layer and the application layer. It mirrors the
LootBox ORM columns and exposes to_dict() for JSON serialisation in FastAPI
responses.
"""

from __future__ import annotations

from database.card import CardDTO


class LootBoxDTO:
    """
    DTO for the LootBox ORM model.

    Attributes:
        id (int | None): Primary key (None before insertion).
        name (str): Name of the loot box.
        description (str): Description of the loot box.
        price (int): Price of the loot box.
        nbr_random_cards (int): Number of random cards in the loot box.
        mandatory_cards (list[tuple[CardDTO, int]]): List of mandatory card DTOs with their quantities.
        random_cards (list[tuple[CardDTO, float]]): List of random card DTOs with their probabilities.
    """

    def __init__(
        self,
        name: str,
        description: str,
        price: int,
        nbr_random_cards: int,
        artwork: str | None = None,
        animations: dict | None = None,
        mandatory_cards: list[tuple[CardDTO, int]] | None = None,
        random_cards: list[tuple[CardDTO, float]] | None = None,
        id: int | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.artwork = artwork
        self.animations = animations
        self.nbr_random_cards = nbr_random_cards
        self.mandatory_cards = mandatory_cards or []
        self.random_cards = random_cards or []

    def __repr__(self) -> str:
        return f"LootBoxDTO(id={self.id}, name={self.name!r}, price={self.price!r})"

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "artwork": self.artwork,
            "animations": self.animations,
            "nbr_random_cards": self.nbr_random_cards,
            "mandatory_cards": [
                {"card": card.to_dict(), "quantity": quantity}
                for card, quantity in self.mandatory_cards
            ],
            "random_cards": [
                {"card": card.to_dict(), "probability": probability}
                for card, probability in self.random_cards
            ],
        }
