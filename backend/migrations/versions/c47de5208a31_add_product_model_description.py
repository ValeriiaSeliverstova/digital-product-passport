"""add product model description

Revision ID: c47de5208a31
Revises: b32a1c9e7410
Create Date: 2026-08-07 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c47de5208a31"
down_revision: str | Sequence[str] | None = "b32a1c9e7410"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add an optional shared description to product models."""

    op.add_column(
        "product_models",
        sa.Column("description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove the product model description."""

    op.drop_column("product_models", "description")
