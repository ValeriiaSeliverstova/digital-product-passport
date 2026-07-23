from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.template_field import TemplateFieldResponse


TemplateStatus = Literal["draft", "active", "archived"]


class PassportTemplateCreate(BaseModel):
    """Request body for creating a draft passport template."""

    category_id: UUID
    name: str = Field(min_length=1, max_length=255)
    version: int = Field(default=1, ge=1, le=2_147_483_647)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class PassportTemplateUpdate(BaseModel):
    """Editable template metadata and lifecycle status."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: TemplateStatus | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @model_validator(mode="after")
    def require_a_change(self) -> "PassportTemplateUpdate":
        if self.name is None and self.status is None:
            raise ValueError("Provide a name or status to update")
        return self


class PassportTemplateResponse(BaseModel):
    """Passport template metadata returned by list and write endpoints."""

    id: UUID
    organization_id: UUID
    category_id: UUID
    name: str
    version: int
    status: TemplateStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PassportTemplateDetailResponse(PassportTemplateResponse):
    """Passport template metadata together with its ordered fields."""

    fields: list[TemplateFieldResponse]
