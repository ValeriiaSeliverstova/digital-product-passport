"""add support tickets

Revision ID: 15a8c2d04e6f
Revises: 7be35a70cd21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "15a8c2d04e6f"
down_revision: str | None = "7be35a70cd21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_item_id", sa.Uuid(), nullable=False),
        sa.Column("azure_ticket_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("tracking_code_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "tracking_email_sent",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("azure_ticket_id"),
        sa.UniqueConstraint(
            "product_item_id",
            "idempotency_key",
            name="uq_support_ticket_item_idempotency_key",
        ),
    )
    op.create_index(
        op.f("ix_support_tickets_organization_id"),
        "support_tickets",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_product_item_id"),
        "support_tickets",
        ["product_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_support_tickets_product_item_id"),
        table_name="support_tickets",
    )
    op.drop_index(
        op.f("ix_support_tickets_organization_id"),
        table_name="support_tickets",
    )
    op.drop_table("support_tickets")
