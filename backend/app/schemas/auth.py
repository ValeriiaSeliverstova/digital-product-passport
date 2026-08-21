from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
)

from app.schemas.user import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


class TokenResponse(BaseModel):
    """OAuth2 access token returned after successful login."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class ForgotPasswordRequest(BaseModel):
    """Email address supplied without revealing whether an account exists."""

    email: Annotated[str, Field(min_length=3, max_length=320)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    """Private reset token and replacement password."""

    token: Annotated[str, Field(min_length=32, max_length=256)]
    new_password: Annotated[
        SecretStr,
        Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH),
    ]


class AuthMessageResponse(BaseModel):
    """Generic authentication workflow confirmation."""

    message: str


class SignupRequest(BaseModel):
    """Public registration details for one manufacturer administrator."""

    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[
        SecretStr,
        Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH),
    ]
    organization_name: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("first_name", "last_name", "organization_name")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        # A whitespace-only value satisfies min_length, so reject it here.
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        # Same normalization and shape check as technician account creation,
        # so signup and login agree on what one address means.
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

    # Forbidding unknown keys keeps organization_id, role_id, role names, and
    # status out of a public request. The backend assigns all of them.
    model_config = ConfigDict(extra="forbid")


class ConfirmEmailRequest(BaseModel):
    """Private confirmation token taken from the emailed link."""

    token: Annotated[str, Field(min_length=32, max_length=256)]

    model_config = ConfigDict(extra="forbid")


class SignupResponse(BaseModel):
    """Safe confirmation of a newly registered manufacturer account."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    status: str
    role: str
    organization_id: UUID
    organization_name: str
