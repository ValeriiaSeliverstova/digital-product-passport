"""add organization contact fields

Revision ID: a6f19c8d2e47
Revises: e58f5d92ac14
Create Date: 2026-08-09 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a6f19c8d2e47"
down_revision: str | Sequence[str] | None = "e58f5d92ac14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add optional postal and electronic organization contact details."""

    op.add_column(
        "organizations",
        sa.Column("address_line_1", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("city", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("postal_code", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("contact_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("phone", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("website", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    """Remove organization postal and electronic contact details."""

    op.drop_column("organizations", "website")
    op.drop_column("organizations", "phone")
    op.drop_column("organizations", "contact_email")
    op.drop_column("organizations", "postal_code")
    op.drop_column("organizations", "city")
    op.drop_column("organizations", "address_line_2")
    op.drop_column("organizations", "address_line_1")
