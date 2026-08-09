"""add organization logo

Revision ID: c84d91e26f30
Revises: f3b8c2d7a914
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c84d91e26f30"
down_revision: str | None = "f3b8c2d7a914"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("logo_data", sa.LargeBinary(), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("logo_content_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("logo_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "logo_updated_at")
    op.drop_column("organizations", "logo_content_type")
    op.drop_column("organizations", "logo_data")
