"""add lifecycle events table

Revision ID: f3b8c2d7a914
Revises: a6f19c8d2e47
Create Date: 2026-08-09 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f3b8c2d7a914"
down_revision: str | Sequence[str] | None = "a6f19c8d2e47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create auditable lifecycle history for physical product items."""

    op.create_table(
        "lifecycle_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("service_provider", sa.String(length=255), nullable=True),
        sa.Column(
            "access_level",
            sa.String(length=50),
            server_default="manufacturer",
            nullable=False,
        ),
        sa.Column(
            "event_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "access_level IN ('public', 'manufacturer')",
            name="ck_lifecycle_event_access_level",
        ),
        sa.CheckConstraint(
            "event_type IN ("
            "'manufacturing', 'installation', 'inspection', 'maintenance', "
            "'repair', 'certification', 'retirement'"
            ")",
            name="ck_lifecycle_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["product_items.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lifecycle_events_item_occurred_at",
        "lifecycle_events",
        ["item_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove product lifecycle history."""

    op.drop_index(
        "ix_lifecycle_events_item_occurred_at",
        table_name="lifecycle_events",
    )
    op.drop_table("lifecycle_events")
