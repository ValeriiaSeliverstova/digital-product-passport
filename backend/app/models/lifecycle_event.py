from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.product_item import ProductItem
    from app.models.user import User


# SQLite supports lightweight tests, while PostgreSQL stores searchable JSONB.
EVENT_DATA_TYPE = JSON().with_variant(JSONB(), "postgresql")


class LifecycleEvent(Base):
    """A dated event in the history of one physical product item."""

    __tablename__ = "lifecycle_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'manufacturing', 'installation', 'inspection', 'maintenance', "
            "'repair', 'certification', 'retirement'"
            ")",
            name="ck_lifecycle_event_type",
        ),
        CheckConstraint(
            "access_level IN ('public', 'manufacturer')",
            name="ck_lifecycle_event_access_level",
        ),
        Index(
            "ix_lifecycle_events_item_occurred_at",
            "item_id",
            "occurred_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_items.id"),
        nullable=False,
    )

    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    service_provider: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    access_level: Mapped[str] = mapped_column(
        String(50),
        default="manufacturer",
        server_default="manufacturer",
        nullable=False,
    )

    event_data: Mapped[dict[str, Any]] = mapped_column(
        EVENT_DATA_TYPE,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    product_item: Mapped[ProductItem] = relationship(
        back_populates="lifecycle_events",
    )
    created_by: Mapped[User] = relationship()
