"""add product models table

Revision ID: b32a1c9e7410
Revises: 4f6c2a91b8de
Create Date: 2026-08-07 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b32a1c9e7410"
down_revision: str | Sequence[str] | None = "4f6c2a91b8de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table used to register manufacturer product models."""

    op.create_table(
        "product_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("model_code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_product_model_status",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["product_categories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["passport_templates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "model_code",
            name="uq_product_model_owner_code",
        ),
    )
    op.create_index(
        op.f("ix_product_models_category_id"),
        "product_models",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_models_organization_id"),
        "product_models",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_models_template_id"),
        "product_models",
        ["template_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the product models table."""

    op.drop_index(
        op.f("ix_product_models_template_id"),
        table_name="product_models",
    )
    op.drop_index(
        op.f("ix_product_models_organization_id"),
        table_name="product_models",
    )
    op.drop_index(
        op.f("ix_product_models_category_id"),
        table_name="product_models",
    )
    op.drop_table("product_models")
