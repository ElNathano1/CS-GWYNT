"""
DTOs for Effect and Trigger database entities.

TriggerDTO and EffectDTO are plain Python objects (no SQLAlchemy dependency)
used to transfer data between the database layer and the application layer.
They mirror the Trigger and Effect ORM columns and expose to_dict() for JSON
serialisation in FastAPI responses.
"""

from __future__ import annotations

import json


class TriggerDTO:
    """
    DTO for the Trigger ORM model.

    Attributes:
        id (int | None): Primary key (None before insertion).
        event (str): Event name that can fire this trigger.
        activate_on_logic (str | None): Logic operator for activation conditions.
        activate_on_conditions (list[dict] | None): Conditions to activate the trigger.
        deactivate_on_logic (str | None): Logic operator for deactivation conditions.
        deactivate_on_conditions (list[dict] | None): Conditions to deactivate the trigger.
        fire_when_logic (str | None): Logic operator for fire-when conditions.
        fire_when_conditions (list[dict] | None): Conditions required to fire.
        countdown (int): Turns before the trigger becomes active.
        repeat_limit (int | None): Maximum number of times the trigger can fire (None = unlimited).
        repeat_interval (int): Minimum turns between consecutive fires.
        initially_active (int): Whether the trigger starts active (1) or inactive (0).
    """

    def __init__(
        self,
        event: str,
        id: int | None = None,
        activate_on_logic: str | None = None,
        activate_on_conditions: list[dict] | None = None,
        deactivate_on_logic: str | None = None,
        deactivate_on_conditions: list[dict] | None = None,
        fire_when_logic: str | None = None,
        fire_when_conditions: list[dict] | None = None,
        countdown: int = 0,
        repeat_limit: int | None = None,
        repeat_interval: int = 0,
        initially_active: int = 1,
    ):
        self.id = id
        self.event = event
        self.activate_on_logic = activate_on_logic
        self.activate_on_conditions = activate_on_conditions
        self.deactivate_on_logic = deactivate_on_logic
        self.deactivate_on_conditions = deactivate_on_conditions
        self.fire_when_logic = fire_when_logic
        self.fire_when_conditions = fire_when_conditions
        self.countdown = countdown
        self.repeat_limit = repeat_limit
        self.repeat_interval = repeat_interval
        self.initially_active = initially_active

    def __repr__(self) -> str:
        return (
            f"TriggerDTO(id={self.id}, event={self.event!r}, "
            f"countdown={self.countdown}, repeat_limit={self.repeat_limit})"
        )

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "event": self.event,
            "activate_on": (
                {
                    "logic": self.activate_on_logic,
                    "conditions": self.activate_on_conditions,
                }
                if self.activate_on_logic is not None
                else None
            ),
            "deactivate_on": (
                {
                    "logic": self.deactivate_on_logic,
                    "conditions": self.deactivate_on_conditions,
                }
                if self.deactivate_on_logic is not None
                else None
            ),
            "fire_when": (
                {
                    "logic": self.fire_when_logic,
                    "conditions": self.fire_when_conditions,
                }
                if self.fire_when_logic is not None
                else None
            ),
            "countdown": self.countdown,
            "repeat_limit": self.repeat_limit,
            "repeat_interval": self.repeat_interval,
            "initially_active": self.initially_active,
        }

    @staticmethod
    def _parse_conditions(raw: str | None) -> list[dict] | None:
        if raw is None:
            return None
        decoded = json.loads(raw)
        if isinstance(decoded, list):
            return [c for c in decoded if isinstance(c, dict)]
        return None


class EffectDTO:
    """
    DTO for the Effect ORM model.

    Attributes:
        id (int | None): Primary key (None before insertion).
        description (str): Human-readable description of the effect.
        type (str): Effect type identifier (e.g. "boost", "debuff").
        target_shape (str | None): Shape descriptor for the target (e.g. "single", "row").
        target_payload (dict | None): Full target payload as a dictionary.
        trigger (TriggerDTO | None): The associated trigger DTO.
        value (int | None): Simple integer value for the effect (mutually exclusive with value_data).
        value_data (dict | None): Complex value payload (mutually exclusive with value).
    """

    def __init__(
        self,
        description: str,
        type: str,
        id: int | None = None,
        artwork: str | None = None,
        target_shape: str | None = None,
        target_payload: dict | None = None,
        trigger: TriggerDTO | None = None,
        value: int | None = None,
        value_data: dict | None = None,
        animations: dict | None = None,
    ):
        self.id = id
        self.description = description
        self.type = type
        self.artwork = artwork
        self.target_shape = target_shape
        self.target_payload = target_payload
        self.trigger = trigger
        self.value = value
        self.value_data = value_data
        self.animations = animations

    def __repr__(self) -> str:
        return (
            f"EffectDTO(id={self.id}, type={self.type!r}, "
            f"description={self.description!r})"
        )

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "artwork": self.artwork,
            "target": (
                {"shape": self.target_shape, **self.target_payload}
                if self.target_payload is not None
                else ({"shape": self.target_shape} if self.target_shape else None)
            ),
            "trigger": self.trigger.to_dict() if self.trigger else None,
            "value": self.value if self.value_data is None else self.value_data,
            "animations": self.animations,
        }
