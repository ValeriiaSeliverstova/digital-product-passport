from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeamMemberCreate(BaseModel):
    """Address invited to create one organization service-technician account.

    No password is accepted here. The technician chooses their own through the
    emailed invitation link, so a credential never travels by email.
    """

    email: str = Field(min_length=3, max_length=320)

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
    # "pending" covers an invited technician who has not chosen a password yet.
    status: Literal["active", "inactive", "pending"]
    role: str

