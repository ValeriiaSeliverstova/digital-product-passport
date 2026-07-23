from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.product_category import ProductCategory
    from app.models.template_field import TemplateField


class PassportTemplate(Base):
    """A versioned passport structure owned by one manufacturer."""

    __tablename__ = "passport_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "category_id",
            "name",
            "version",
            name="uq_template_owner_category_name_version",
        ),
        CheckConstraint("version >= 1", name="ck_template_version_positive"),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_template_status",
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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        server_default="draft",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship()
    category: Mapped[ProductCategory] = relationship()
    fields: Mapped[list[TemplateField]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateField.display_order",
    )
