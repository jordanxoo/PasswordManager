"""add_vault_category

Revision ID: a21d20e51eb5
Revises: 90773a98bfa2
Create Date: 2026-05-11 15:10:36.669899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a21d20e51eb5'
down_revision: Union[str, Sequence[str], None] = '90773a98bfa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("CREATE TYPE category AS ENUM ('social', 'work', 'finance', 'email', 'other')")
    op.add_column('vaults', sa.Column('category', sa.Enum('social', 'work', 'finance','email', 'other', name='category'), nullable=True))

def downgrade():
    op.drop_column('vaults', 'category')
    op.execute("DROP TYPE category")
