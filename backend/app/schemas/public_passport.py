from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.template_field import FieldDataType


class PublicPassportField(BaseModel):
    """One public template field together with its product-specific value."""

    code: str
    label: str
    data_type: FieldDataType
    value: Any


class PublicLifecycleEvent(BaseModel):
    """One lifecycle event intentionally shared on the public passport."""

    id: UUID
    event_type: Literal[
        "manufacturing",
        "installation",
        "inspection",
        "maintenance",
        "repair",
        "certification",
        "retirement",
    ]
    occurred_at: datetime
    description: str | None
    service_provider: str | None
    event_data: dict[str, Any]


class PublicPassportResponse(BaseModel):
    """Safe product information displayed without authentication."""

    public_id: UUID
    manufacturer_name: str
    manufacturer_logo_path: str | None
    support_email: str | None
    support_phone: str | None
    support_website: str | None
    category_name: str
    model_code: str
    model_name: str
    model_description: str | None
    template_name: str
    template_version: int
    serial_number: str
    manufacture_date: date | None
    fields: list[PublicPassportField]
    lifecycle_events: list[PublicLifecycleEvent]
