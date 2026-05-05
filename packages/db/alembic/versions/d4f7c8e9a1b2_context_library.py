"""context_library

Revision ID: d4f7c8e9a1b2
Revises: b1d26d39f399
Create Date: 2026-04-24 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4f7c8e9a1b2'
down_revision: Union[str, Sequence[str], None] = 'b1d26d39f399'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'context_entries',
        sa.Column('user_id', sa.Uuid(), nullable=False, comment='Owner user.'),
        sa.Column('title', sa.String(200), nullable=False, comment='Short label shown in the UI.'),
        sa.Column('content', sa.Text(), nullable=False, comment='The full text that gets embedded and retrieved.'),
        sa.Column('category', sa.String(100), nullable=True, comment="Top-level category."),
        sa.Column('subcategory', sa.String(100), nullable=True, comment="Sub-category."),
        sa.Column('source_type', sa.String(50), server_default='manual', nullable=False, comment='Origin: manual | session | archive.'),
        sa.Column('source_id', sa.String(200), nullable=True, comment='conversation_id or document_id when auto-extracted.'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='If false, excluded from RAG retrieval.'),
        sa.Column('id', sa.Uuid(), nullable=False, comment='Primary key (UUIDv4).'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_context_entries_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_context_entries')),
        comment='User knowledge fragments for RAG retrieval.',
    )
    op.create_index('ix_context_entries_user_id', 'context_entries', ['user_id'])
    op.create_index('ix_context_entries_category', 'context_entries', ['category'])


def downgrade() -> None:
    op.drop_index('ix_context_entries_category', table_name='context_entries')
    op.drop_index('ix_context_entries_user_id', table_name='context_entries')
    op.drop_table('context_entries')
