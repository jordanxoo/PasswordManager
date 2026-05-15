"""add_hibp_event_types

Revision ID: 16c503b0664a
Revises: reconcile_missing
Create Date: 2026-05-15 11:57:03.285470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16c503b0664a'
down_revision: Union[str, Sequence[str], None] = 'reconcile_missing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'HIBP_PASSWORD_CHECK'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'HIBP_EMAIL_CHECK'")



def downgrade():
    pass

