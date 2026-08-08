from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr


MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


class PasswordChangeRequest(BaseModel):
    """Passwords supplied when an authenticated user changes credentials."""

    current_password: SecretStr
    new_password: Annotated[
        SecretStr,
        Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH),
    ]


class RoleResponse(BaseModel):
    """Role information safe to expose through the API."""

    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    """Organization details safe to show to an authenticated member."""

    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Authenticated user information without password data."""

    id: UUID
    organization_id: UUID | None
    organization: OrganizationResponse | None
    email: str
    status: str
    role: RoleResponse

    model_config = ConfigDict(from_attributes=True)
