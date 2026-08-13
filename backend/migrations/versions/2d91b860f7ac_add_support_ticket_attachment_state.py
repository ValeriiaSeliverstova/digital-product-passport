"""add support ticket attachment state

Revision ID: 2d91b860f7ac
Revises: 15a8c2d04e6f
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "2d91b860f7ac"
down_revision: str | None = "15a8c2d04e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "support_tickets",
        sa.Column(
            "attachment_added",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("support_tickets", "attachment_added")
