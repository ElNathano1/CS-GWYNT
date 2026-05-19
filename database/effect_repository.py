"""
Data access layer for Effect and Trigger entities.

EffectRepository encapsulates all database operations for creating, reading,
updating, and deleting Effect and Trigger records. It translates between
SQLAlchemy ORM models (Effect, Trigger) and the EffectDTO / TriggerDTO classes.
"""

from __future__ import annotations

import json
from typing import cast

from sqlalchemy.orm import Session

from database.effect import EffectDTO, TriggerDTO
from database.models import Effect, Trigger


class EffectRepository:
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    # Internal helpers

    def _orm_trigger_to_dto(self, trigger: Trigger) -> TriggerDTO:
        """Convert a Trigger ORM object to a TriggerDTO."""
        return TriggerDTO(
            id=trigger.id,  # type: ignore
            event=trigger.event,  # type: ignore
            activate_on_logic=cast(str | None, trigger.activate_on_logic),
            activate_on_conditions=TriggerDTO._parse_conditions(
                cast(str | None, trigger.activate_on_conditions)
            ),
            deactivate_on_logic=cast(str | None, trigger.deactivate_on_logic),
            deactivate_on_conditions=TriggerDTO._parse_conditions(
                cast(str | None, trigger.deactivate_on_conditions)
            ),
            fire_when_logic=cast(str | None, trigger.fire_when_logic),
            fire_when_conditions=TriggerDTO._parse_conditions(
                cast(str | None, trigger.fire_when_conditions)
            ),
            countdown=trigger.countdown,  # type: ignore
            repeat_limit=cast(int | None, trigger.repeat_limit),
            repeat_interval=trigger.repeat_interval,  # type: ignore
            initially_active=trigger.initially_active,  # type: ignore
        )

    def _orm_effect_to_dto(self, effect: Effect) -> EffectDTO:
        """Convert an Effect ORM object to an EffectDTO."""
        trigger_dto = (
            self._orm_trigger_to_dto(effect.trigger)  # type: ignore
            if effect.trigger  # type: ignore
            else None
        )

        target_payload = effect.get_target()
        target_shape = cast(str | None, effect.target_shape)

        value_data = effect.get_value_data()
        simple_value: int | None = None
        complex_value: dict | None = None
        if isinstance(value_data, int):
            simple_value = value_data
        elif isinstance(value_data, dict):
            complex_value = value_data

        return EffectDTO(
            id=effect.id,  # type: ignore
            description=effect.description,  # type: ignore
            type=effect.type,  # type: ignore
            target_shape=target_shape,
            target_payload=target_payload,
            trigger=trigger_dto,
            value=simple_value,
            value_data=complex_value,
        )

    def _apply_trigger_dto(self, orm: Trigger, dto: TriggerDTO) -> None:
        """Write TriggerDTO fields into a Trigger ORM object (in-place)."""
        orm.event = dto.event  # type: ignore
        orm.countdown = dto.countdown  # type: ignore
        orm.repeat_limit = dto.repeat_limit  # type: ignore
        orm.repeat_interval = dto.repeat_interval  # type: ignore
        orm.initially_active = dto.initially_active  # type: ignore

        def _encode(
            logic: str | None, conditions: list[dict] | None
        ) -> tuple[str | None, str | None]:
            return logic, (json.dumps(conditions) if conditions is not None else None)

        al, ac = _encode(dto.activate_on_logic, dto.activate_on_conditions)
        dl, dc = _encode(dto.deactivate_on_logic, dto.deactivate_on_conditions)
        fl, fc = _encode(dto.fire_when_logic, dto.fire_when_conditions)

        orm.activate_on_logic = al  # type: ignore
        orm.activate_on_conditions = ac  # type: ignore
        orm.deactivate_on_logic = dl  # type: ignore
        orm.deactivate_on_conditions = dc  # type: ignore
        orm.fire_when_logic = fl  # type: ignore
        orm.fire_when_conditions = fc  # type: ignore

    # Trigger CRUD

    def create_trigger(self, dto: TriggerDTO) -> TriggerDTO:
        """
        Persist a new Trigger record.

        Args:
            dto: TriggerDTO to persist (id is ignored and overwritten)

        Returns:
            TriggerDTO with the assigned database id
        """
        orm = Trigger()
        self._apply_trigger_dto(orm, dto)
        self.session.add(orm)
        self.session.commit()
        self.session.refresh(orm)
        return self._orm_trigger_to_dto(orm)

    def get_trigger(self, trigger_id: int) -> TriggerDTO | None:
        """
        Retrieve a trigger by its primary key.

        Args:
            trigger_id: The primary key of the trigger

        Returns:
            TriggerDTO if found, None otherwise
        """
        orm = self.session.query(Trigger).filter_by(id=trigger_id).first()
        if not orm:
            return None
        return self._orm_trigger_to_dto(orm)

    def get_triggers_by_event(self, event: str) -> list[TriggerDTO]:
        """
        Retrieve all triggers for a given event name.

        Args:
            event: The event name to filter by

        Returns:
            List of TriggerDTO objects
        """
        orms = self.session.query(Trigger).filter_by(event=event).all()
        return [self._orm_trigger_to_dto(o) for o in orms]

    def update_trigger(self, dto: TriggerDTO) -> TriggerDTO | None:
        """
        Update an existing trigger.

        Args:
            dto: TriggerDTO with updated fields (must have a valid id)

        Returns:
            Updated TriggerDTO, or None if the trigger was not found
        """
        if dto.id is None:
            return None
        orm = self.session.query(Trigger).filter_by(id=dto.id).first()
        if not orm:
            return None
        self._apply_trigger_dto(orm, dto)
        self.session.commit()
        return self._orm_trigger_to_dto(orm)

    def delete_trigger(self, trigger_id: int) -> bool:
        """
        Delete a trigger by its primary key.

        Args:
            trigger_id: The primary key of the trigger to delete

        Returns:
            True if deleted, False if not found
        """
        orm = self.session.query(Trigger).filter_by(id=trigger_id).first()
        if not orm:
            return False
        self.session.delete(orm)
        self.session.commit()
        return True

    # Effect CRUD

    def create_effect(self, dto: EffectDTO) -> EffectDTO:
        """
        Persist a new Effect (and its Trigger if provided) as a single transaction.

        Args:
            dto: EffectDTO to persist (id is ignored and overwritten)

        Returns:
            EffectDTO with assigned database ids (effect and trigger)
        """
        # Persist trigger first so we have its id
        trigger_orm: Trigger | None = None
        if dto.trigger is not None:
            trigger_orm = Trigger()
            self._apply_trigger_dto(trigger_orm, dto.trigger)
            self.session.add(trigger_orm)
            self.session.flush()  # get trigger_orm.id without committing yet

        orm = Effect(
            description=dto.description,
            type=dto.type,
            trigger_id=trigger_orm.id if trigger_orm else None,
        )
        orm.set_target(dto.target_payload)
        orm.set_value_data(dto.value_data if dto.value_data is not None else dto.value)
        self.session.add(orm)
        self.session.commit()
        self.session.refresh(orm)
        return self._orm_effect_to_dto(orm)

    def get_effect(self, effect_id: int) -> EffectDTO | None:
        """
        Retrieve an effect (with its trigger) by primary key.

        Args:
            effect_id: The primary key of the effect

        Returns:
            EffectDTO if found, None otherwise
        """
        orm = self.session.query(Effect).filter_by(id=effect_id).first()
        if not orm:
            return None
        return self._orm_effect_to_dto(orm)

    def get_effects_by_type(self, effect_type: str) -> list[EffectDTO]:
        """
        Retrieve all effects of a given type.

        Args:
            effect_type: The effect type string to filter by

        Returns:
            List of EffectDTO objects
        """
        orms = self.session.query(Effect).filter_by(type=effect_type).all()
        return [self._orm_effect_to_dto(o) for o in orms]

    def get_all_effects(self) -> list[EffectDTO]:
        """
        Retrieve all effects from the database.

        Returns:
            List of EffectDTO objects
        """
        orms = self.session.query(Effect).all()
        return [self._orm_effect_to_dto(o) for o in orms]

    def update_effect(self, dto: EffectDTO) -> EffectDTO | None:
        """
        Update an existing effect and its linked trigger.

        Args:
            dto: EffectDTO with updated fields (must have a valid id)

        Returns:
            Updated EffectDTO, or None if the effect was not found
        """
        if dto.id is None:
            return None
        orm = self.session.query(Effect).filter_by(id=dto.id).first()
        if not orm:
            return None

        orm.description = dto.description  # type: ignore
        orm.type = dto.type  # type: ignore
        orm.set_target(dto.target_payload)
        orm.set_value_data(dto.value_data if dto.value_data is not None else dto.value)

        if dto.trigger is not None:
            if orm.trigger:  # type: ignore
                self._apply_trigger_dto(orm.trigger, dto.trigger)  # type: ignore
            else:
                trigger_orm = Trigger()
                self._apply_trigger_dto(trigger_orm, dto.trigger)
                self.session.add(trigger_orm)
                self.session.flush()
                orm.trigger_id = trigger_orm.id  # type: ignore

        self.session.commit()
        return self._orm_effect_to_dto(orm)

    def delete_effect(self, effect_id: int) -> bool:
        """
        Delete an effect (and its trigger) by primary key.

        Args:
            effect_id: The primary key of the effect to delete

        Returns:
            True if deleted, False if not found
        """
        orm = self.session.query(Effect).filter_by(id=effect_id).first()
        if not orm:
            return False
        trigger = orm.trigger  # type: ignore
        self.session.delete(orm)
        if trigger:
            self.session.delete(trigger)
        self.session.commit()
        return True
