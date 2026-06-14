"""add organizations, memberships, user keypair and vault org_id

Revision ID: f1a2b3c4d5e6
Revises: b1c2d3e4f5a6
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New audit event types (stored by enum member name, like existing migrations).
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'ORG_CREATED'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'ORG_MEMBER_ADDED'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'ORG_MEMBER_REMOVED'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'ORG_ROLE_CHANGED'")

    # Create the enum type idempotently in SQL (SQLAlchemy's checkfirst is
    # unreliable under asyncpg). create_table below references it with
    # create_type=False so it is never auto-created a second time.
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orgrole') THEN "
        "CREATE TYPE orgrole AS ENUM ('OWNER', 'ADMIN', 'MEMBER'); "
        "END IF; END $$;"
    )
    orgrole = ENUM('OWNER', 'ADMIN', 'MEMBER', name='orgrole', create_type=False)

    # Asymmetric keypair columns on users (nullable for legacy accounts).
    op.add_column('users', sa.Column('public_key', sa.String(), nullable=True))
    op.add_column('users', sa.Column('encrypted_private_key', sa.String(), nullable=True))
    op.add_column('users', sa.Column('private_key_iv', sa.String(), nullable=True))

    op.create_table(
        'organizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'organization_memberships',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', orgrole, nullable=False),
        sa.Column('wrapped_org_key', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('org_id', 'user_id', name='uq_org_member'),
    )

    op.add_column('vaults', sa.Column('org_id', UUID(as_uuid=True),
                                      sa.ForeignKey('organizations.id'), nullable=True))
    op.create_index('ix_vaults_org_id', 'vaults', ['org_id'])


def downgrade() -> None:
    op.drop_index('ix_vaults_org_id', table_name='vaults')
    op.drop_column('vaults', 'org_id')
    op.drop_table('organization_memberships')
    op.drop_table('organizations')
    op.drop_column('users', 'private_key_iv')
    op.drop_column('users', 'encrypted_private_key')
    op.drop_column('users', 'public_key')
    sa.Enum(name='orgrole').drop(op.get_bind(), checkfirst=True)
    # eventtype enum values are not removed (Postgres cannot drop enum values).
