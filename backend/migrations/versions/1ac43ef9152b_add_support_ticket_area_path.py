"""add support ticket area path

Revision ID: 1ac43ef9152b
Revises: f91be36d704a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "1ac43ef9152b"
down_revision: str | None = "f91be36d704a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("azure_devops_area_path", sa.String(length=400), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "azure_devops_area_path")
