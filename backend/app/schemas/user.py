from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    """Role information safe to expose through the API."""

    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Authenticated user information without password data."""

    id: UUID
    organization_id: UUID | None
    email: str
    status: str
    role: RoleResponse

    model_config = ConfigDict(from_attributes=True)
