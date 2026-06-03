"""drop plaintext vault name/url (moved into the encrypted blob)

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-03

"""
from alembic import op
import sqlalchemy as sa

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("vaults", "name")
    op.drop_column("vaults", "url")
    op.drop_column("vault_history", "name")
    op.drop_column("vault_history", "url")


def downgrade() -> None:
    op.add_column("vaults", sa.Column("name", sa.String(), nullable=False, server_default=""))
    op.add_column("vaults", sa.Column("url", sa.String(), nullable=False, server_default=""))
    op.add_column("vault_history", sa.Column("name", sa.String(), nullable=False, server_default=""))
    op.add_column("vault_history", sa.Column("url", sa.String(), nullable=False, server_default=""))
