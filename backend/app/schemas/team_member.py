from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.schemas.user import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


class TeamMemberCreate(BaseModel):
    """Initial credentials for one organization service technician."""

    email: str = Field(min_length=3, max_length=320)
    initial_password: Annotated[
        SecretStr,
        Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH),
    ]

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local_part, separator, domain = normalized.partition("@")
        if (
            not separator
            or not local_part
            or "." not in domain
            or any(character.isspace() for character in normalized)
        ):
            raise ValueError("Enter a valid email address")
        return normalized

    model_config = ConfigDict(extra="forbid")


class TeamMemberUpdate(BaseModel):
    """Editable account state for an existing service technician."""

    status: Literal["active", "inactive"]

    model_config = ConfigDict(extra="forbid")


class TeamMemberResponse(BaseModel):
    """Safe organization team-member data without password information."""

    id: UUID
    email: str
    status: Literal["active", "inactive"]
    role: str

