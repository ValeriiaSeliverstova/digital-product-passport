"""add service technicians and product-item creator

Revision ID: 83fc92ea104d
Revises: 2d91b860f7ac
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision: str = "83fc92ea104d"
down_revision: str | None = "2d91b860f7ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
    )
    connection = op.get_bind()
    existing_role = connection.execute(
        sa.select(roles.c.id).where(roles.c.name == "service_technician"),
    ).scalar_one_or_none()
    if existing_role is None:
        op.bulk_insert(
            roles,
            [{"id": uuid4(), "name": "service_technician"}],
        )
    op.add_column(
        "product_items",
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_product_items_created_by_user_id_users",
        "product_items",
        "users",
        ["created_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_product_items_created_by_user_id_users",
        "product_items",
        type_="foreignkey",
    )
    op.drop_column("product_items", "created_by_user_id")
    op.execute("DELETE FROM roles WHERE name = 'service_technician'")
