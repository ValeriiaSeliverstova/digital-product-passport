from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProductCategory(Base):
    """A system-managed category that can belong to a category hierarchy."""

    __tablename__ = "product_categories"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    parent_category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_categories.id"),
        nullable=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    parent: Mapped[ProductCategory | None] = relationship(
        remote_side=[id],
        back_populates="children",
    )

    children: Mapped[list[ProductCategory]] = relationship(
        back_populates="parent",
    )
