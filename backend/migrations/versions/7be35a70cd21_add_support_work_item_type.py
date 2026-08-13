"""add support work item type

Revision ID: 7be35a70cd21
Revises: 1ac43ef9152b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "7be35a70cd21"
down_revision: str | None = "1ac43ef9152b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "azure_devops_work_item_type",
            sa.String(length=128),
            server_default="Customer Support",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "azure_devops_work_item_type")
