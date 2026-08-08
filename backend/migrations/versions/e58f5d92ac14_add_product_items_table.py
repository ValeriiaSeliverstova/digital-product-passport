"""add product items table

Revision ID: e58f5d92ac14
Revises: c47de5208a31
Create Date: 2026-08-07 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e58f5d92ac14"
down_revision: str | Sequence[str] | None = "c47de5208a31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table for individual physical products and passport data."""

    op.create_table(
        "product_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("manufacture_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "passport_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name="ck_product_item_status",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["product_models.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "serial_number",
            name="uq_product_item_owner_serial",
        ),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index(
        op.f("ix_product_items_model_id"),
        "product_items",
        ["model_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_items_organization_id"),
        "product_items",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the product items table."""

    op.drop_index(
        op.f("ix_product_items_organization_id"),
        table_name="product_items",
    )
    op.drop_index(
        op.f("ix_product_items_model_id"),
        table_name="product_items",
    )
    op.drop_table("product_items")
