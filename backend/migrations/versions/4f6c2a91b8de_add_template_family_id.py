"""add template family id

Revision ID: 4f6c2a91b8de
Revises: d21cbbf86149
Create Date: 2026-08-04 00:00:00.000000
"""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "4f6c2a91b8de"
down_revision: str | Sequence[str] | None = "d21cbbf86149"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add and backfill the stable identifier shared by template versions."""

    op.add_column(
        "passport_templates",
        sa.Column("template_family_id", sa.Uuid(), nullable=True),
    )

    # Existing versions were identified by owner, category, and name. Give all
    # rows in each existing group the same family UUID before making it required.
    templates = sa.table(
        "passport_templates",
        sa.column("id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("category_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("template_family_id", sa.Uuid()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            templates.c.id,
            templates.c.organization_id,
            templates.c.category_id,
            templates.c.name,
        ),
    ).mappings()

    family_ids: dict[tuple[object, object, str], object] = {}
    for row in rows:
        family_key = (
            row["organization_id"],
            row["category_id"],
            row["name"],
        )
        family_id = family_ids.setdefault(family_key, uuid4())
        connection.execute(
            templates.update()
            .where(templates.c.id == row["id"])
            .values(template_family_id=family_id),
        )

    op.alter_column(
        "passport_templates",
        "template_family_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_template_family_version",
        "passport_templates",
        ["template_family_id", "version"],
    )
    op.create_index(
        "ix_passport_templates_template_family_id",
        "passport_templates",
        ["template_family_id"],
        unique=False,
    )


def downgrade() -> None:
    """Restore name-based version grouping."""

    op.drop_index(
        "ix_passport_templates_template_family_id",
        table_name="passport_templates",
    )
    op.drop_constraint(
        "uq_template_family_version",
        "passport_templates",
        type_="unique",
    )
    op.drop_column("passport_templates", "template_family_id")
