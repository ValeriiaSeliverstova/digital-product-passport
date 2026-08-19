"""add user names

Revision ID: b4d1f07c92ae
Revises: 6cb70911fc44
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b4d1f07c92ae"
down_revision: str | None = "6cb70911fc44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing accounts predate public signup and keep NULL names.
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
