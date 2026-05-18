"""
DTO for the Achievement database entity.

AchievementDTO is a plain Python object (no SQLAlchemy dependency) used to
transfer achievement data between the database layer and the application layer.
"""

from __future__ import annotations


class AchievementDTO:
    """
    DTO for the Achievement ORM model.

    Attributes:
        id (int | None): Primary key (None before insertion).
        name (str): Name of the achievement.
        description (str): Human-readable description of the achievement.
        criteria (str): Unlock criteria (e.g. "Win 10 games").
        illustration (str | None): Optional thumbnail/illustration path or URL.
    """

    def __init__(
        self,
        name: str,
        description: str,
        criteria: str,
        illustration: str | None = None,
        id: int | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.criteria = criteria
        self.illustration = illustration

    def __repr__(self) -> str:
        return f"AchievementDTO(id={self.id}, name={self.name!r})"

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "criteria": self.criteria,
            "illustration": self.illustration,
        }
