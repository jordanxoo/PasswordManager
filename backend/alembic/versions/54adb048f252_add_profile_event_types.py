"""add_profile_event_types

Revision ID: 54adb048f252
Revises: 9b202612ebbe
Create Date: 2026-05-11 15:27:56.475806

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54adb048f252'
down_revision: Union[str, Sequence[str], None] = '9b202612ebbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("ALTER TYPE eventtype ADD VALUE 'email_changed'")
    op.execute("ALTER TYPE eventtype ADD VALUE 'password_changed'")
    op.execute("ALTER TYPE eventtype ADD VALUE 'account_deleted'")
    op.execute("ALTER TYPE eventtype ADD VALUE 'session_revoked'")




def downgrade() -> None:
    """Downgrade schema."""
    pass
