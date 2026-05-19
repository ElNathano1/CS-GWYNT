"""
Data access layer for Card entities.

CardRepository encapsulates all database operations for creating, reading,
updating, and deleting Card records. It translates between the SQLAlchemy ORM
Card model and the CardDTO class.

Effect and Trigger creation is delegated to EffectRepository so that each
repository has a single responsibility.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from database.card import CardDTO
from database.effect import EffectDTO
from database.effect_repository import EffectRepository
from database.models import Card, Effect


class CardRepository:
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self._effect_repo = EffectRepository(session)

    # Internal helper

    def _orm_to_dto(self, orm: Card) -> CardDTO:
        """Convert a Card ORM object to a CardDTO."""
        effect_dto: EffectDTO | None = None
        if orm.effect:  # type: ignore
            effect_dto = self._effect_repo._orm_effect_to_dto(orm.effect)  # type: ignore

        return CardDTO(
            id=orm.id,  # type: ignore
            name=orm.name,  # type: ignore
            description=orm.description,  # type: ignore
            rarity=orm.rarity,  # type: ignore
            power_table=orm.power_table,  # type: ignore
            face_artwork_url=cast(str | None, orm.face_artwork_url),
            back_artwork_url=cast(str | None, orm.back_artwork_url),
            effect=effect_dto,
        )

    # CRUD

    def create(self, dto: CardDTO) -> CardDTO:
        """
        Persist a new card (and its effect + trigger if provided).

        If dto.effect is set, the effect (and its trigger) are created first via
        EffectRepository, then linked to the new card.

        Args:
            dto: CardDTO to persist (id is ignored and overwritten)

        Returns:
            CardDTO with assigned database id
        """
        effect_id: int | None = None
        if dto.effect is not None:
            persisted_effect = self._effect_repo.create_effect(dto.effect)
            effect_id = persisted_effect.id

        orm = Card(
            name=dto.name,
            description=dto.description,
            rarity=dto.rarity,
            power_table=dto.power_table,
            face_artwork_url=dto.face_artwork_url,
            back_artwork_url=dto.back_artwork_url,
            effect_id=effect_id,
            buying_price=dto.buying_price,
            selling_price=dto.selling_price,
        )
        self.session.add(orm)
        self.session.commit()
        self.session.refresh(orm)
        return self._orm_to_dto(orm)

    def get(self, card_id: int) -> CardDTO | None:
        """
        Retrieve a card by its primary key.

        Args:
            card_id: The primary key of the card

        Returns:
            CardDTO if found, None otherwise
        """
        orm = self.session.query(Card).filter_by(id=card_id).first()
        if not orm:
            return None
        return self._orm_to_dto(orm)

    def get_by_name(self, name: str) -> CardDTO | None:
        """
        Retrieve a card by its exact name.

        Args:
            name: The name of the card

        Returns:
            CardDTO if found, None otherwise
        """
        orm = self.session.query(Card).filter_by(name=name).first()
        if not orm:
            return None
        return self._orm_to_dto(orm)

    def get_all(self) -> list[CardDTO]:
        """
        Retrieve all cards from the database.

        Returns:
            List of CardDTO objects
        """
        orms = self.session.query(Card).all()
        return [self._orm_to_dto(o) for o in orms]

    def get_by_rarity(self, rarity: str) -> list[CardDTO]:
        """
        Retrieve all cards of a given rarity.

        Args:
            rarity: The rarity string to filter by (e.g. "common", "rare")

        Returns:
            List of CardDTO objects
        """
        orms = self.session.query(Card).filter_by(rarity=rarity).all()
        return [self._orm_to_dto(o) for o in orms]

    def update(self, dto: CardDTO) -> CardDTO | None:
        """
        Update an existing card's metadata.

        Updating the linked effect is delegated to EffectRepository.update_effect().
        Call that method separately if you also need to change the effect/trigger.

        Args:
            dto: CardDTO with updated fields (must have a valid id)

        Returns:
            Updated CardDTO, or None if the card was not found
        """
        if dto.id is None:
            return None
        orm = self.session.query(Card).filter_by(id=dto.id).first()
        if not orm:
            return None

        orm.name = dto.name  # type: ignore
        orm.description = dto.description  # type: ignore
        orm.rarity = dto.rarity  # type: ignore
        orm.power_table = dto.power_table  # type: ignore
        orm.face_artwork_url = dto.face_artwork_url  # type: ignore
        orm.back_artwork_url = dto.back_artwork_url  # type: ignore
        orm.buying_price = dto.buying_price  # type: ignore
        orm.selling_price = dto.selling_price  # type: ignore
        # Attach a new effect if one is provided and none currently exists
        if dto.effect is not None and orm.effect is None:  # type: ignore
            persisted_effect = self._effect_repo.create_effect(dto.effect)
            orm.effect_id = persisted_effect.id  # type: ignore

        self.session.commit()
        return self._orm_to_dto(orm)

    def delete(self, card_id: int) -> bool:
        """
        Delete a card by its primary key.

        The linked effect and trigger are also deleted if present.

        Args:
            card_id: The primary key of the card to delete

        Returns:
            True if deleted, False if not found
        """
        orm = self.session.query(Card).filter_by(id=card_id).first()
        if not orm:
            return False
        effect: Effect | None = orm.effect  # type: ignore
        self.session.delete(orm)
        if effect:
            self._effect_repo.delete_effect(effect.id)  # type: ignore
        else:
            self.session.commit()
        return True

    def search(self, query: str) -> list[CardDTO]:
        """
        Search cards by partial name match (case-insensitive).

        Args:
            query: Substring to search for in card names

        Returns:
            List of matching CardDTO objects
        """
        orms = (
            self.session.query(Card)
            .filter(Card.name.ilike(f"%{query}%"))  # type: ignore
            .all()
        )
        return [self._orm_to_dto(o) for o in orms]
