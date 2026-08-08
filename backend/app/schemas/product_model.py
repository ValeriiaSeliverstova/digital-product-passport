from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProductModelStatus = Literal["active", "archived"]


class ProductModelCreate(BaseModel):
    """Request body for registering a product model."""

    category_id: UUID
    template_id: UUID
    model_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=2_000)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ProductModelUpdate(BaseModel):
    """Fields that may change after a product model is created."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=2_000)
    status: ProductModelStatus | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @model_validator(mode="after")
    def require_a_change(self) -> "ProductModelUpdate":
        # An explicitly provided null description is valid and clears the text.
        if not self.model_fields_set:
            raise ValueError("Provide a name, description, or status to update")
        return self


class ProductModelResponse(BaseModel):
    """Product model data returned by the API."""

    id: UUID
    organization_id: UUID
    category_id: UUID
    template_id: UUID
    model_code: str
    name: str
    description: str | None
    status: ProductModelStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
