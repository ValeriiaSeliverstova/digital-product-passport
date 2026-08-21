"""add invitation tokens

Revision ID: f7c3b91d42ea
Revises: d5e2a83c41bf
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f7c3b91d42ea"
down_revision: str | None = "d5e2a83c41bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invitation_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_invitation_tokens_user_id"),
        "invitation_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_invitation_tokens_user_id"),
        table_name="invitation_tokens",
    )
    op.drop_table("invitation_tokens")
