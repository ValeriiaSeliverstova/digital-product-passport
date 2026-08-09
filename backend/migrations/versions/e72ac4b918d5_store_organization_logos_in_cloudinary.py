"""store organization logos in Cloudinary

Revision ID: e72ac4b918d5
Revises: c84d91e26f30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e72ac4b918d5"
down_revision: str | None = "c84d91e26f30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("logo_public_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
    )
    # Existing database-stored logos must be uploaded again through Profile.
    op.drop_column("organizations", "logo_content_type")
    op.drop_column("organizations", "logo_data")


def downgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("logo_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("logo_content_type", sa.String(length=50), nullable=True),
    )
    op.drop_column("organizations", "logo_url")
    op.drop_column("organizations", "logo_public_id")
