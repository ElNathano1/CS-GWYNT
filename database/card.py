"""
DTO for the Card database entity.

CardDTO is a plain Python object (no SQLAlchemy dependency) used to transfer
card data between the database layer and the application layer. It mirrors the
Card ORM columns and exposes to_dict() for JSON serialisation in FastAPI
responses.
"""

from __future__ import annotations

from database.effect import EffectDTO


class CardDTO:
    """
    DTO for the Card ORM model.

    Attributes:
        id (int | None): Primary key (None before insertion).
        name (str): Name of the card.
        description (str): Description of the card.
        rarity (str): Rarity tier (e.g. "common", "rare", "legendary").
        power_table (str): Serialised power table for gameplay.
        face_artwork_url (str | None): URL or path for the card's face artwork.
        back_artwork_url (str | None): URL or path for the card's back artwork.
        effect (EffectDTO | None): The associated effect DTO, if any.
        buying_price (int): The in-game currency cost to buy the card.
        selling_price (int): The in-game currency value when selling the card.
    """

    def __init__(
        self,
        name: str,
        description: str,
        rarity: str,
        power_table: str,
        id: int | None = None,
        face_artwork_url: str | None = None,
        back_artwork_url: str | None = None,
        animations: dict | None = None,
        effect: EffectDTO | None = None,
        buying_price: int = 0,
        selling_price: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.rarity = rarity
        self.power_table = power_table
        self.face_artwork_url = face_artwork_url
        self.back_artwork_url = back_artwork_url
        self.animations = animations
        self.effect = effect
        self.buying_price = buying_price
        self.selling_price = selling_price

    def __repr__(self) -> str:
        return f"CardDTO(id={self.id}, name={self.name!r}, rarity={self.rarity!r})"

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rarity": self.rarity,
            "power_table": self.power_table,
            "face_artwork_url": self.face_artwork_url,
            "back_artwork_url": self.back_artwork_url,
            "animations": self.animations,
            "effect": self.effect.to_dict() if self.effect else None,
            "buying_price": self.buying_price,
            "selling_price": self.selling_price,
        }
