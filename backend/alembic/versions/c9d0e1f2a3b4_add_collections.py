"""add collections, collection_access and vaults.collection_id

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'collections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'collection_access',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('collections.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('wrapped_collection_key', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('collection_id', 'user_id', name='uq_collection_member'),
    )
    op.create_index('ix_collection_access_collection_id', 'collection_access', ['collection_id'])
    op.add_column('vaults', sa.Column('collection_id', UUID(as_uuid=True),
                                      sa.ForeignKey('collections.id'), nullable=True))
    op.create_index('ix_vaults_collection_id', 'vaults', ['collection_id'])


def downgrade() -> None:
    op.drop_index('ix_vaults_collection_id', table_name='vaults')
    op.drop_column('vaults', 'collection_id')
    op.drop_index('ix_collection_access_collection_id', table_name='collection_access')
    op.drop_table('collection_access')
    op.drop_table('collections')
