from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.role import Role


class User(Base):
    """An authenticated platform user with one assigned role."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # Platform administrators may have no organization. Organization
    # administrators and technicians must be linked to one; application
    # authorization enforces that rule.
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=True,
    )

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id"),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
    )

    # Names are optional because seeded, script-created, and technician
    # accounts are created without them. Public signup always supplies both.
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        server_default="active",
        nullable=False,
    )

    organization: Mapped[Organization | None] = relationship(
        back_populates="users",
    )

    role: Mapped[Role] = relationship(
        back_populates="users",
    )
