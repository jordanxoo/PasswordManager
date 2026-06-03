"""add_recovery_event_types

Revision ID: b1c2d3e4f5a6
Revises: d2e3f4a5b6c7
Create Date: 2026-06-03 16:20:00.000000

Adds the recovery-code audit event types. Without these the eventtype enum
rejects them and any /auth/2fa/recovery/* log_event call 500s.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'RECOVERY_CODES_GENERATED'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'RECOVERY_CODES_USED'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'RECOVERY_CODE_FAILED'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
