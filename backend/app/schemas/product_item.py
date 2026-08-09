from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProductItemStatus = Literal["draft", "published", "retired"]
PassportData = dict[str, Any]


class ProductItemCreate(BaseModel):
    """Request body for registering one physical product as a draft."""

    model_id: UUID
    serial_number: str = Field(min_length=1, max_length=100)
    manufacture_date: date | None = None
    passport_data: PassportData = Field(default_factory=dict, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ProductItemUpdate(BaseModel):
    """Editable product values and lifecycle status."""

    serial_number: str | None = Field(default=None, min_length=1, max_length=100)
    manufacture_date: date | None = None
    passport_data: PassportData | None = Field(default=None, max_length=100)
    status: ProductItemStatus | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @model_validator(mode="after")
    def require_a_change(self) -> "ProductItemUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        if "serial_number" in self.model_fields_set and self.serial_number is None:
            raise ValueError("serial_number cannot be null")
        if "passport_data" in self.model_fields_set and self.passport_data is None:
            raise ValueError("passport_data cannot be null")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be null")
        return self


class ProductItemResponse(BaseModel):
    """Product item data returned to its manufacturer."""

    id: UUID
    organization_id: UUID
    model_id: UUID
    serial_number: str
    public_id: UUID
    manufacture_date: date | None
    status: ProductItemStatus
    passport_data: PassportData
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductItemListItem(BaseModel):
    """Compact product-item data used by the paginated list screen."""

    id: UUID
    model_id: UUID
    model_name: str
    serial_number: str
    public_id: UUID
    manufacture_date: date | None
    status: ProductItemStatus
    created_at: datetime


class ProductItemPage(BaseModel):
    """One filtered page of manufacturer-owned product items."""

    items: list[ProductItemListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
