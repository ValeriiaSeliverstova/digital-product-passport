from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.passport_template import PassportTemplate


# SQLite supports JSON in tests, while PostgreSQL uses queryable JSONB.
VALIDATION_RULES_TYPE = JSON().with_variant(JSONB(), "postgresql")


class TemplateField(Base):
    """A configurable field belonging to one passport template."""

    __tablename__ = "template_fields"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "code",
            name="uq_template_field_code",
        ),
        CheckConstraint(
            "data_type IN ('text', 'integer', 'decimal', 'boolean', 'date')",
            name="ck_template_field_data_type",
        ),
        CheckConstraint(
            "access_level IN ('public', 'manufacturer')",
            name="ck_template_field_access_level",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_template_field_display_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("passport_templates.id"),
        index=True,
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    access_level: Mapped[str] = mapped_column(
        String(50),
        default="public",
        server_default="public",
        nullable=False,
    )

    validation_rules: Mapped[dict[str, Any]] = mapped_column(
        VALIDATION_RULES_TYPE,
        default=dict,
        nullable=False,
    )

    template: Mapped[PassportTemplate] = relationship(
        back_populates="fields",
    )
