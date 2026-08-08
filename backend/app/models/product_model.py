from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.passport_template import PassportTemplate
    from app.models.product_category import ProductCategory
    from app.models.product_item import ProductItem


class ProductModel(Base):
    """A manufacturer's product design linked to one template version."""

    __tablename__ = "product_models"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "model_code",
            name="uq_product_model_owner_code",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_product_model_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
        nullable=False,
    )

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_categories.id"),
        index=True,
        nullable=False,
    )

    # This references one exact template version, not the whole family.
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("passport_templates.id"),
        index=True,
        nullable=False,
    )

    model_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        server_default="active",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship()
    category: Mapped[ProductCategory] = relationship()
    template: Mapped[PassportTemplate] = relationship()
    items: Mapped[list[ProductItem]] = relationship(
        back_populates="product_model",
    )
