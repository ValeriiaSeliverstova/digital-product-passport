from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SupportTicketCreate(BaseModel):
    """Customer details and problem text submitted from a public passport."""

    requester_name: str = Field(min_length=1, max_length=100)
    requester_email: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=10, max_length=5000)

    @field_validator("requester_email")
    @classmethod
    def validate_requester_email(cls, value: str) -> str:
        """Apply the same lightweight email validation used by profiles."""

        local_part, separator, domain = value.partition("@")
        if (
            not separator
            or not local_part
            or "." not in domain
            or any(character.isspace() for character in value)
        ):
            raise ValueError("Enter a valid email address")
        return value.lower()

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class SupportTicketResponse(BaseModel):
    """Safe Azure DevOps identifiers returned after ticket creation."""

    ticket_id: int


class SupportTicketTrackRequest(BaseModel):
    """Private code sent to the customer after ticket creation."""

    tracking_code: str = Field(min_length=16, max_length=64)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class SupportTicketReplyRequest(SupportTicketTrackRequest):
    """Tracking credentials and a new customer message."""

    message: str = Field(min_length=1, max_length=2000)


class SupportTicketCommentResponse(BaseModel):
    """Customer-safe representation of an Azure work-item comment."""

    id: int
    author: str
    message: str
    created_at: datetime


class SupportTicketStatusResponse(BaseModel):
    """Small customer-safe status view derived from Azure DevOps."""

    ticket_id: int
    subject: str
    status: str
    submitted_at: datetime
    updated_at: datetime | None
    comments: list[SupportTicketCommentResponse]
