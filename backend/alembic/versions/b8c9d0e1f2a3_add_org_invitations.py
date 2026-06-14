"""add organization_invitations and make membership wrapped_org_key nullable

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pending-confirmation members have no org key yet.
    op.alter_column('organization_memberships', 'wrapped_org_key',
                    existing_type=sa.String(), nullable=True)

    # orgrole type already exists from an earlier migration.
    orgrole = ENUM('OWNER', 'ADMIN', 'MEMBER', name='orgrole', create_type=False)
    op.create_table(
        'organization_invitations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', orgrole, nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('invited_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_org_invitations_token_hash', 'organization_invitations', ['token_hash'])


def downgrade() -> None:
    op.drop_index('ix_org_invitations_token_hash', table_name='organization_invitations')
    op.drop_table('organization_invitations')
    op.alter_column('organization_memberships', 'wrapped_org_key',
                    existing_type=sa.String(), nullable=False)
