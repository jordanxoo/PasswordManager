"""fix_category_enum_case

Revision ID: 9b202612ebbe
Revises: a21d20e51eb5
Create Date: 2026-05-11 15:16:17.410022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b202612ebbe'
down_revision: Union[str, Sequence[str], None] = 'a21d20e51eb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_column('vaults', 'category')
    op.execute("DROP TYPE category")
    op.execute("CREATE TYPE category AS ENUM ('SOCIAL', 'WORK', 'FINANCE', 'EMAIL', 'OTHER')")
    op.add_column('vaults', sa.Column('category',
        sa.Enum('SOCIAL', 'WORK', 'FINANCE', 'EMAIL', 'OTHER', name='category'),
        nullable=True))

def downgrade():
    op.drop_column('vaults', 'category')
    op.execute("DROP TYPE category")
    op.execute("CREATE TYPE category AS ENUM ('social', 'work', 'finance', 'email', 'other')")
    op.add_column('vaults', sa.Column('category',
        sa.Enum('social', 'work', 'finance', 'email', 'other', name='category'),
        nullable=True))
