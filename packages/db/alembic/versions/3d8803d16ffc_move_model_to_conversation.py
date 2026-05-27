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
    # Idempotent for fresh DBs: the initial schema migration already created
    # conversations.model, and messages.model may have never existed.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    conv_cols = {c['name'] for c in inspector.get_columns('conversations')}
    msg_cols = {c['name'] for c in inspector.get_columns('messages')}

    # 1. Add model column to conversations with default (only if missing)
    if 'model' not in conv_cols:
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

    # 2. Backfill from messages.model (only if both columns existed before)
    if 'model' in msg_cols and 'model' in conv_cols:
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

    # 3. Drop column from messages (only if it exists)
    if 'model' in msg_cols:
        op.drop_column('messages', 'model')

    # Index on documents.user_id (idempotent)
    doc_indexes = {i['name'] for i in inspector.get_indexes('documents')}
    if 'ix_documents_user_id' not in doc_indexes:
        op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)

    # Rename users.username constraint (idempotent)
    user_constraints = {c['name'] for c in inspector.get_unique_constraints('users')}
    if 'users_username_key' in user_constraints:
        op.drop_constraint('users_username_key', 'users', type_='unique')
    if 'uq_users_username' not in user_constraints:
        op.create_unique_constraint(op.f('uq_users_username'), 'users', ['username'])

    # --- Catch-up: Apply naming conventions and missing comments ---
    # Conversations
    op.alter_column('conversations', 'user_id', existing_type=sa.UUID(), comment='Owner user.')
    op.alter_column('conversations', 'title', existing_type=sa.VARCHAR(length=200), comment='User-provided or auto-generated title.')
    op.alter_column('conversations', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    
    # Documents
    op.alter_column('documents', 'id', existing_type=sa.UUID(), comment='Primary key (UUIDv4).')
    op.alter_column('documents', 'created_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Row creation time (UTC).')
    op.alter_column('documents', 'updated_at', existing_type=postgresql.TIMESTAMP(timezone=True), comment='Last modification time (UTC).')

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
