"""
Data access layer for Achievement entities.

AchievementRepository encapsulates all database operations for creating,
reading, updating, and deleting Achievement records. It translates between
the SQLAlchemy ORM Achievement model and the AchievementDTO class.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.achievement import AchievementDTO
from database.models import Achievement


class AchievementRepository:
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    # ─────────────────────────── internal helper ────────────────────────────

    def _orm_to_dto(self, orm: Achievement) -> AchievementDTO:
        """Convert an Achievement ORM object to an AchievementDTO."""
        return AchievementDTO(
            id=orm.id,  # type: ignore
            name=orm.name,  # type: ignore
            description=orm.description,  # type: ignore
            criteria=orm.criteria,  # type: ignore
            illustration=orm.illustration,  # type: ignore
        )

    # ──────────────────────────── CRUD ──────────────────────────────────────

    def create(self, dto: AchievementDTO) -> AchievementDTO:
        """
        Persist a new achievement.

        Args:
            dto: AchievementDTO to persist (id is ignored and overwritten)

        Returns:
            AchievementDTO with the assigned database id
        """
        orm = Achievement(
            name=dto.name,
            description=dto.description,
            criteria=dto.criteria,
            illustration=dto.illustration,
        )
        self.session.add(orm)
        self.session.commit()
        self.session.refresh(orm)
        return self._orm_to_dto(orm)

    def get(self, achievement_id: int) -> AchievementDTO | None:
        """
        Retrieve an achievement by its primary key.

        Args:
            achievement_id: The primary key of the achievement

        Returns:
            AchievementDTO if found, None otherwise
        """
        orm = self.session.query(Achievement).filter_by(id=achievement_id).first()
        if not orm:
            return None
        return self._orm_to_dto(orm)

    def get_by_name(self, name: str) -> AchievementDTO | None:
        """
        Retrieve an achievement by its exact name.

        Args:
            name: The name of the achievement

        Returns:
            AchievementDTO if found, None otherwise
        """
        orm = self.session.query(Achievement).filter_by(name=name).first()
        if not orm:
            return None
        return self._orm_to_dto(orm)

    def get_all(self) -> list[AchievementDTO]:
        """
        Retrieve all achievements from the database.

        Returns:
            List of AchievementDTO objects
        """
        orms = self.session.query(Achievement).all()
        return [self._orm_to_dto(o) for o in orms]

    def update(self, dto: AchievementDTO) -> AchievementDTO | None:
        """
        Update an existing achievement.

        Args:
            dto: AchievementDTO with updated fields (must have a valid id)

        Returns:
            Updated AchievementDTO, or None if not found
        """
        if dto.id is None:
            return None
        orm = self.session.query(Achievement).filter_by(id=dto.id).first()
        if not orm:
            return None
        orm.name = dto.name  # type: ignore
        orm.description = dto.description  # type: ignore
        orm.criteria = dto.criteria  # type: ignore
        orm.illustration = dto.illustration  # type: ignore
        self.session.commit()
        return self._orm_to_dto(orm)

    def delete(self, achievement_id: int) -> bool:
        """
        Delete an achievement by its primary key.

        Note: all AchievementsCorrespondancy rows referencing this achievement
        will be cascade-deleted by the ORM.

        Args:
            achievement_id: The primary key of the achievement to delete

        Returns:
            True if deleted, False if not found
        """
        orm = self.session.query(Achievement).filter_by(id=achievement_id).first()
        if not orm:
            return False
        self.session.delete(orm)
        self.session.commit()
        return True
