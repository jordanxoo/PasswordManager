"""add vault pinned

Revision ID: c1d2e3f4a5b6
Revises: feab0c99ff3c
Create Date: 2026-06-03

"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "feab0c99ff3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vaults",
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("vaults", "pinned")
