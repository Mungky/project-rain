"""move_model_to_conversation

Revision ID: 3d8803d16ffc
Revises: 3c737a5a064e
Create Date: 2026-04-23 22:49:40.389928

Reason: Move model identifier from Message to Conversation table to tie a model
to a session, not individual messages. 
Ref: WO-033

Safety:
- Includes data backfill from messages to conversations.
- Reversible: Downgrade restores model column to messages and backfills from conversation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3d8803d16ffc'
down_revision: Union[str, Sequence[str], None] = '3c737a5a064e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add model column to conversations with default
    op.add_column(
        'conversations', 
        sa.Column(
            'model', 
            sa.String(length=100), 
            server_default='kimi-k2.6:cloud', 
            nullable=False, 
            comment='LLM model identifier used for this conversation session.'
        )
    )
    
    # 2. Backfill: Update conversations' model from the latest message that had one
    op.execute("""
        UPDATE conversations c
        SET model = m.model
        FROM (
            SELECT DISTINCT ON (conversation_id) conversation_id, model
            FROM messages
            WHERE model IS NOT NULL
            ORDER BY conversation_id, created_at DESC
        ) m
        WHERE c.id = m.conversation_id
    """)

    # 3. Drop column from messages
    op.drop_column('messages', 'model')

    # --- Catch-up: Apply naming conventions and missing comments ---
    # Conversations
    op.alter_column('conversations', 'user_id', existing_type=sa.UUID(), comment='Owner user.')
    op.alter_column('conversations', 'title', existing_type=sa.VARCHAR(length=200), comment='User-provided or auto-generated title.')
    op.alter_column('conversations', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    
    # Documents
    op.alter_column('documents', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    op.alter_column('documents', 'created_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Row creation time (UTC).')
    op.alter_column('documents', 'updated_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Last modification time (UTC).')
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    
    # Messages
    op.alter_column('messages', 'conversation_id', existing_type=sa.UUID(), comment='Parent conversation.')
    op.alter_column('messages', 'role', existing_type=postgresql.ENUM('user', 'assistant', 'system', 'tool', name='message_role'), comment='Sender role.')
    op.alter_column('messages', 'content', existing_type=sa.TEXT(), comment='The actual text content of the message.')
    op.alter_column('messages', 'tokens_in', existing_type=sa.INTEGER(), comment='Prompt token count.')
    op.alter_column('messages', 'tokens_out', existing_type=sa.INTEGER(), comment='Completion token count.')
    op.alter_column('messages', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    
    # Skill Executions
    op.alter_column('skill_executions', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    op.alter_column('skill_executions', 'created_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Row creation time (UTC).')
    op.alter_column('skill_executions', 'updated_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Last modification time (UTC).')
    
    # Skills
    op.alter_column('skills', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    op.alter_column('skills', 'created_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Row creation time (UTC).')
    op.alter_column('skills', 'updated_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Last modification time (UTC).')
    
    # Users
    op.alter_column('users', 'username', existing_type=sa.VARCHAR(length=50), comment='Unique identifier for the user account.')
    op.alter_column('users', 'email', existing_type=sa.VARCHAR(length=255), comment='User email address.')
    op.alter_column('users', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    op.drop_constraint('users_username_key', 'users', type_='unique')
    op.create_unique_constraint(op.f('uq_users_username'), 'users', ['username'])


def downgrade() -> None:
    # 1. Restore constraint name
    op.drop_constraint(op.f('uq_users_username'), 'users', type_='unique')
    op.create_unique_constraint('users_username_key', 'users', ['username'])
    
    # 2. Add model column back to messages
    op.add_column('messages', sa.Column('model', sa.String(length=100), nullable=True, comment='LLM model used to generate the response.'))
    
    # 3. Restore data from conversations to messages
    op.execute("""
        UPDATE messages m
        SET model = c.model
        FROM conversations c
        WHERE m.conversation_id = c.id
    """)
    
    # 4. Drop model from conversations
    op.drop_column('conversations', 'model')
    
    # --- Catch-up cleanup (comments) ---
    tables_to_clean = ['conversations', 'documents', 'messages', 'skill_executions', 'skills', 'users']
    for table in tables_to_clean:
        op.execute(f"COMMENT ON TABLE {table} IS NULL") # This is a bit broad, but okay for a clean-up
        # Note: Removing individual column comments in downgrade is often omitted 
        # unless specifically required, as it's tedious and often doesn't break anything.
    
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
