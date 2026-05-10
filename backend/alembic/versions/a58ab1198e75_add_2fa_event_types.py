"""add_2fa_event_types

Revision ID: a58ab1198e75
Revises: 90e358558ab0
Create Date: 2026-05-10 17:36:59.034596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a58ab1198e75'
down_revision: Union[str, Sequence[str], None] = '90e358558ab0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE eventtype ADD VALUE 'TWO_FA_ENABLED'")                        
    op.execute("ALTER TYPE eventtype ADD VALUE 'TWO_FA_DISABLED'")                       
    op.execute("ALTER TYPE eventtype ADD VALUE 'TWO_FA_FAILED'")                         
    op.execute("ALTER TYPE eventtype ADD VALUE 'TWO_FA_SUCCESS'")       


def downgrade() -> None:
    """Downgrade schema."""
    pass
