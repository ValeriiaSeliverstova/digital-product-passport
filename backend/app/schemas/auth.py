from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

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
