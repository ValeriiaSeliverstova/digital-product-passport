from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.product_model import ProductModel


# SQLite supports JSON in tests, while PostgreSQL stores passport values as JSONB.
PASSPORT_DATA_TYPE = JSON().with_variant(JSONB(), "postgresql")


class ProductItem(Base):
    """One physical product with its own Digital Product Passport data."""

    __tablename__ = "product_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "serial_number",
            name="uq_product_item_owner_serial",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name="ck_product_item_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Direct ownership makes organization isolation and serial uniqueness clear.
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
        nullable=False,
    )

    model_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_models.id"),
        index=True,
        nullable=False,
    )

    serial_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # This random identifier is safe to use later in a public passport URL.
    public_id: Mapped[UUID] = mapped_column(
        default=uuid4,
        unique=True,
        nullable=False,
    )

    manufacture_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        server_default="draft",
        nullable=False,
    )

    passport_data: Mapped[dict[str, Any]] = mapped_column(
        PASSPORT_DATA_TYPE,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship()
    product_model: Mapped[ProductModel] = relationship(back_populates="items")
