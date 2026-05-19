"""
Data access layer for LootBox entities.

LootBoxRepository encapsulates all database operations for creating, reading,
updating, and deleting LootBox records. It translates between the SQLAlchemy ORM
LootBox model and the LootBoxDTO class.

Effect and Trigger creation is delegated to EffectRepository so that each
repository has a single responsibility.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.loot_box import LootBoxDTO
from database.card import CardDTO
from database.card_repository import CardRepository
from database.models import (
    LootBox,
    Card,
    LootBoxMandatoryCards,
    LootBoxRandomCards,
    UserLootBoxCorrespondancy,
)


def random_choice_weighted(choices: list[tuple[CardDTO, float]]) -> CardDTO:
    """
    Select a random card from a list of (card, probability) pairs.

    Args:
        choices: List of tuples where each tuple contains a CardDTO and its associated probability.

    Returns:
        A randomly selected CardDTO based on the provided probabilities.
    """
    import random

    if not choices:
        raise ValueError("No random card choices available")

    weighted_choices = [(card, max(0.0, prob)) for card, prob in choices]
    total = sum(prob for _, prob in weighted_choices)
    if total <= 0:
        raise ValueError("Random card probabilities must sum to a positive value")

    r = random.random() * total
    upto = 0
    for card, prob in weighted_choices:
        if upto + prob >= r:
            return card
        upto += prob

    return weighted_choices[-1][0]


class LootBoxRepository:
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self._card_repo = CardRepository(session)

    # Internal helper

    def _orm_to_dto(self, orm: LootBox) -> LootBoxDTO:
        """Convert a LootBox ORM object to a LootBoxDTO."""
        mandatory_correspondances = (
            self.session.query(LootBoxMandatoryCards)
            .filter_by(loot_box_id=orm.id)  # type: ignore
            .all()
        )
        random_correspondances = (
            self.session.query(LootBoxRandomCards)
            .filter_by(loot_box_id=orm.id)  # type: ignore
            .all()
        )
        mandatory_cards = [
            (self._card_repo._orm_to_dto(correspondance.card), correspondance.quantity)
            for correspondance in mandatory_correspondances
        ]
        random_cards = [
            (
                self._card_repo._orm_to_dto(correspondance.card),
                correspondance.probability,
            )
            for correspondance in random_correspondances
        ]

        return LootBoxDTO(
            id=orm.id,  # type: ignore
            name=orm.name,  # type: ignore
            description=orm.description,  # type: ignore
            price=orm.price,  # type: ignore
            nbr_random_cards=orm.nbr_random_cards,  # type: ignore
            artwork=orm.artwork,  # type: ignore
            animations=orm.get_animations(),  # type: ignore
            mandatory_cards=mandatory_cards,  # type: ignore
            random_cards=random_cards,  # type: ignore
        )

    # CRUD

    def create(self, dto: LootBoxDTO) -> LootBoxDTO:
        """
        Persist a new loot box (and its cards if provided).

        If dto.effect is set, the effect (and its trigger) are created first via
        EffectRepository, then linked to the new card.

        Args:
            dto: LootBoxDTO to persist (id is ignored and overwritten)

        Returns:
            LootBoxDTO with assigned database id
        """
        orm = LootBox(
            name=dto.name,
            description=dto.description,
            price=dto.price,
            nbr_random_cards=dto.nbr_random_cards,
            artwork=dto.artwork,
        )
        orm.set_animations(dto.animations)
        self.session.add(orm)
        self.session.flush()

        for card_dto, quantity in dto.mandatory_cards:
            if card_dto.id is None:
                continue

            correspondance = (
                self.session.query(LootBoxMandatoryCards)
                .filter_by(loot_box_id=orm.id, card_id=card_dto.id)
                .first()
            )
            if correspondance:
                correspondance.quantity += quantity  # type: ignore
            else:
                self.session.add(
                    LootBoxMandatoryCards(
                        loot_box_id=orm.id, card_id=card_dto.id, quantity=quantity
                    )
                )

        for card_dto, probability in dto.random_cards:
            if card_dto.id is None:
                continue

            correspondance = (
                self.session.query(LootBoxRandomCards)
                .filter_by(loot_box_id=orm.id, card_id=card_dto.id)
                .first()
            )
            if correspondance:
                correspondance.probability = probability  # type: ignore
            else:
                self.session.add(
                    LootBoxRandomCards(
                        loot_box_id=orm.id,
                        card_id=card_dto.id,
                        probability=probability,
                    )
                )

        self.session.commit()
        self.session.refresh(orm)

        return self._orm_to_dto(orm)

    def add_mandatory_card(
        self, loot_box_id: int, card_id: int, quantity: int = 1
    ) -> bool:
        """
        Add a mandatory card to a loot box.

        Args:
            loot_box_id: The primary key of the loot box
            card_id: The primary key of the card to add
            quantity: The quantity of the card to add

        Returns:
            True if added successfully, False if loot box or card not found
        """
        loot_box = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        card = self.session.query(Card).filter_by(id=card_id).first()
        if not loot_box or not card:
            return False

        correspondance = (
            self.session.query(LootBoxMandatoryCards)
            .filter_by(loot_box_id=loot_box.id, card_id=card.id)
            .first()
        )
        if correspondance:
            correspondance.quantity += quantity  # type: ignore
        else:
            self.session.add(
                LootBoxMandatoryCards(
                    loot_box_id=loot_box.id, card_id=card.id, quantity=quantity
                )
            )
        self.session.commit()
        return True

    def remove_mandatory_card(
        self, loot_box_id: int, card_id: int, quantity: int = 1
    ) -> bool:
        """
        Remove a mandatory card from a loot box.

        Args:
            loot_box_id: The primary key of the loot box
            card_id: The primary key of the card to remove
            quantity: The quantity of the card to remove

        Returns:
            True if removed successfully, False if loot box or card not found
        """
        correspondance = (
            self.session.query(LootBoxMandatoryCards)
            .filter_by(loot_box_id=loot_box_id, card_id=card_id)
            .first()
        )
        if not correspondance:
            return False

        if correspondance.quantity > quantity:  # type: ignore
            correspondance.quantity -= quantity  # type: ignore
        else:
            self.session.delete(correspondance)
        self.session.commit()
        return True

    def add_random_card(
        self, loot_box_id: int, card_id: int, probability: float
    ) -> bool:
        """
        Add a random card to a loot box.

        Args:
            loot_box_id: The primary key of the loot box
            card_id: The primary key of the card to add
            probability: The probability of this card being included in the loot box

        Returns:
            True if added successfully, False if loot box or card not found
        """
        loot_box = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        card = self.session.query(Card).filter_by(id=card_id).first()
        if not loot_box or not card:
            return False

        correspondance = (
            self.session.query(LootBoxRandomCards)
            .filter_by(loot_box_id=loot_box.id, card_id=card.id)
            .first()
        )
        if correspondance:
            correspondance.probability = probability  # type: ignore
        else:
            self.session.add(
                LootBoxRandomCards(
                    loot_box_id=loot_box.id, card_id=card.id, probability=probability
                )
            )
        self.session.commit()
        return True

    def remove_random_card(self, loot_box_id: int, card_id: int) -> bool:
        """
        Remove a random card from a loot box.

        Args:
            loot_box_id: The primary key of the loot box
            card_id: The primary key of the card to remove

        Returns:
            True if removed successfully, False if loot box or card not found
        """
        correspondance = (
            self.session.query(LootBoxRandomCards)
            .filter_by(loot_box_id=loot_box_id, card_id=card_id)
            .first()
        )
        if not correspondance:
            return False

        self.session.delete(correspondance)
        self.session.commit()
        return True

    def get(self, loot_box_id: int) -> LootBoxDTO | None:
        """
        Retrieve a loot box by its primary key.

        Args:
            loot_box_id: The primary key of the loot box

        Returns:
            LootBoxDTO if found, None otherwise
        """
        orm = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        if not orm:
            return None
        return self._orm_to_dto(orm)

    def get_by_name(self, name: str) -> LootBoxDTO | None:
        """
        Retrieve a loot box by its exact name.

        Args:
            name: The name of the loot box

        Returns:
            LootBoxDTO if found, None otherwise
        """
        orm = self.session.query(LootBox).filter_by(name=name).first()
        if not orm:
            return None
        return self._orm_to_dto(orm)  # type: ignore

    def get_all(self) -> list[LootBoxDTO]:
        """
        Retrieve all loot boxes from the database.

        Returns:
            List of LootBoxDTO objects
        """
        orms = self.session.query(LootBox).all()
        return [self._orm_to_dto(o) for o in orms]

    def get_by_rarity(self, rarity: str) -> list[LootBoxDTO]:
        """
        Retrieve all loot boxes of a given rarity.

        Args:
            rarity: The rarity string to filter by (e.g. "common", "rare")

        Returns:
            List of LootBoxDTO objects
        """
        # LootBox has no rarity column; keep compatibility by returning empty results.
        return []

    def update(self, dto: LootBoxDTO) -> LootBoxDTO | None:
        """
        Update an existing loot box's metadata.

        Updating the linked effect is delegated to EffectRepository.update_effect().
        Call that method separately if you also need to change the effect/trigger.

        Args:
            dto: LootBoxDTO with updated fields (must have a valid id)

        Returns:
            Updated LootBoxDTO, or None if the loot box was not found
        """
        if dto.id is None:
            return None
        orm = self.session.query(LootBox).filter_by(id=dto.id).first()
        if not orm:
            return None

        orm.name = dto.name  # type: ignore
        orm.description = dto.description  # type: ignore
        orm.price = dto.price  # type: ignore
        orm.nbr_random_cards = dto.nbr_random_cards  # type: ignore
        orm.artwork = dto.artwork  # type: ignore
        orm.set_animations(dto.animations)

        # Note: Updating cards is not handled here. Use add/remove_mandatory_card and add/remove_random_card for that.

        self.session.commit()
        return self._orm_to_dto(orm)

    def delete(self, loot_box_id: int) -> bool:
        """
        Delete a loot box by its primary key.

        The linked effect and trigger are also deleted if present.

        Args:
            loot_box_id: The primary key of the loot box to delete

        Returns:
            True if deleted, False if not found
        """
        orm = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        if not orm:
            return False
        self.session.delete(orm)
        self.session.commit()
        return True

    def search(self, query: str) -> list[LootBoxDTO]:
        """
        Search loot boxes by partial name match (case-insensitive).

        Args:
            query: Substring to search for in loot box names

        Returns:
            List of matching LootBoxDTO objects
        """
        orms = (
            self.session.query(LootBox)
            .filter(LootBox.name.ilike(f"%{query}%"))  # type: ignore
            .all()
        )
        return [self._orm_to_dto(o) for o in orms]

    def open_loot_box(self, loot_box_id: int) -> list[CardDTO] | None:
        """
        Simulate opening a loot box, returning the list of cards obtained.

        This method does not modify the database (e.g. it does not check or update user inventory).
        It simply applies the loot box logic to determine which cards would be obtained.

        Args:
            loot_box_id: The primary key of the loot box to open

        Returns:
            List of CardDTO objects obtained from the loot box, or None if loot box not found
        """

        loot_box = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        if not loot_box:
            return None

        mandatory_correspondances = (
            self.session.query(LootBoxMandatoryCards)
            .filter_by(loot_box_id=loot_box.id)  # type: ignore
            .all()
        )
        random_correspondances = (
            self.session.query(LootBoxRandomCards)
            .filter_by(loot_box_id=loot_box.id)  # type: ignore
            .all()
        )

        obtained_cards = []
        for correspondance in mandatory_correspondances:
            card_dto = self._card_repo._orm_to_dto(correspondance.card)  # type: ignore
            obtained_cards.extend([card_dto] * correspondance.quantity)  # type: ignore

        random_choices = [
            (self._card_repo._orm_to_dto(correspondance.card), correspondance.probability)  # type: ignore
            for correspondance in random_correspondances
        ]
        if random_choices:
            for _ in range(loot_box.nbr_random_cards):  # type: ignore
                obtained_cards.append(random_choice_weighted(random_choices))  # type: ignore

        return obtained_cards
