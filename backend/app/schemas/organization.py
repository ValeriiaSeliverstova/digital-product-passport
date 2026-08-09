from datetime import datetime
from uuid import UUID
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizationUpdate(BaseModel):
    """Editable organization details for the authenticated manufacturer."""

    name: str = Field(min_length=1, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=30)
    contact_email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=2048)

    @field_validator(
        "country",
        "address_line_1",
        "address_line_2",
        "city",
        "postal_code",
        "contact_email",
        "phone",
        "website",
        mode="before",
    )
    @classmethod
    def empty_optional_value_is_none(cls, value: object) -> object:
        """Treat empty optional form controls as absent values."""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        """Apply basic business-email validation without another dependency."""

        if value is None:
            return None

        local_part, separator, domain = value.partition("@")
        if not separator or not local_part or "." not in domain:
            raise ValueError("Enter a valid contact email address")
        return value.lower()

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: str | None) -> str | None:
        """Accept only absolute HTTP(S) organization websites."""

        if value is None:
            return None

        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("Website must be an absolute HTTP(S) URL")
        return value

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class OrganizationResponse(BaseModel):
    """Organization details safe to expose to an authenticated member."""

    id: UUID
    name: str
    country: str | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    postal_code: str | None
    contact_email: str | None
    phone: str | None
    website: str | None
    has_logo: bool
    logo_updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
