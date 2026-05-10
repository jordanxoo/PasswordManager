"""add_role_and_is_blocked

Revision ID: a676d17c0ebd
Revises: a58ab1198e75
Create Date: 2026-05-10 17:43:35.522118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a676d17c0ebd'
down_revision: Union[str, Sequence[str], None] = 'a58ab1198e75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE role AS ENUM ('USER', 'ADMIN')")                             
    op.add_column('users', sa.Column('role', sa.Enum('USER', 'ADMIN', name='role'),
nullable=False, server_default='USER'))                                                  
    op.add_column('users', sa.Column('is_blocked', sa.Boolean(), nullable=False,
server_default='false'))                                                                 
                       
                                                                                           
def downgrade() -> None:
    op.drop_column('users', 'is_blocked')                                                
    op.drop_column('users', 'role')
    op.execute("DROP TYPE role")
