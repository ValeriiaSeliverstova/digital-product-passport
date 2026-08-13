from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SupportTicket(Base):
    """Local ownership and tracking data for one Azure DevOps support ticket."""

    __tablename__ = "support_tickets"
    __table_args__ = (
        UniqueConstraint(
            "product_item_id",
            "idempotency_key",
            name="uq_support_ticket_item_idempotency_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
        nullable=False,
    )
    product_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_items.id"),
        index=True,
        nullable=False,
    )
    azure_ticket_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    tracking_code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tracking_email_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
