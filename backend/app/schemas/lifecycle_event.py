from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


LifecycleEventType = Literal[
    "manufacturing",
    "installation",
    "inspection",
    "maintenance",
    "repair",
    "certification",
    "retirement",
]
LifecycleEventAccessLevel = Literal["public", "manufacturer"]


class LifecycleEventCreate(BaseModel):
    """Request body for recording an event in a product item's history."""

    event_type: LifecycleEventType
    occurred_at: datetime
    description: str | None = Field(default=None, max_length=2_000)
    service_provider: str | None = Field(default=None, max_length=255)
    access_level: LifecycleEventAccessLevel = "manufacturer"
    event_data: dict[str, Any] = Field(default_factory=dict, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Avoid ambiguous event times from browsers in different regions."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value


class LifecycleEventResponse(BaseModel):
    """Lifecycle-event data returned to its manufacturer."""

    id: UUID
    item_id: UUID
    created_by_user_id: UUID
    event_type: LifecycleEventType
    occurred_at: datetime
    description: str | None
    service_provider: str | None
    access_level: LifecycleEventAccessLevel
    event_data: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
