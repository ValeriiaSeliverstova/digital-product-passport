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
    """Editable family name and template-version lifecycle status."""

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
    template_family_id: UUID
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


class TemplateFamilySummary(PassportTemplateResponse):
    """Latest version and total version count for one template family."""

    version_count: int


class TemplateFamilyPage(BaseModel):
    """One page of filtered template families."""

    items: list[TemplateFamilySummary]
    total: int
    page: int
    page_size: int
    total_pages: int
