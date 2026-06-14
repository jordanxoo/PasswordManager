"""add audit_log.org_id and org/collection audit event types

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in ('ORG_KEY_ROTATED', 'COLLECTION_CREATED', 'COLLECTION_DELETED',
                  'COLLECTION_ACCESS_GRANTED', 'COLLECTION_ACCESS_REVOKED'):
        op.execute(f"ALTER TYPE eventtype ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column('audit_log', sa.Column('org_id', UUID(as_uuid=True),
                                         sa.ForeignKey('organizations.id'), nullable=True))
    op.create_index('ix_audit_log_org_id', 'audit_log', ['org_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_log_org_id', table_name='audit_log')
    op.drop_column('audit_log', 'org_id')
    # eventtype values are not removed (Postgres can't drop enum values).
