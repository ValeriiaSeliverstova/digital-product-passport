"""add product model image

Revision ID: f91be36d704a
Revises: e72ac4b918d5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f91be36d704a"
down_revision: str | None = "e72ac4b918d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_models",
        sa.Column("image_public_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "product_models",
        sa.Column("image_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "product_models",
        sa.Column("image_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_models", "image_updated_at")
    op.drop_column("product_models", "image_url")
    op.drop_column("product_models", "image_public_id")
