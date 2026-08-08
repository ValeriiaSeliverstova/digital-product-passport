from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.template_field import FieldDataType


class PublicPassportField(BaseModel):
    """One public template field together with its product-specific value."""

    code: str
    label: str
    data_type: FieldDataType
    value: Any


class PublicPassportResponse(BaseModel):
    """Safe product information displayed without authentication."""

    public_id: UUID
    manufacturer_name: str
    category_name: str
    model_code: str
    model_name: str
    model_description: str | None
    template_name: str
    template_version: int
    serial_number: str
    manufacture_date: date | None
    fields: list[PublicPassportField]
