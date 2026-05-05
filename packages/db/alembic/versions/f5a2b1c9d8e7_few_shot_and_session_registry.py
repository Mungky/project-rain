"""few_shot_and_session_registry

Revision ID: f5a2b1c9d8e7
Revises: 39b10c768130
Create Date: 2026-05-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f5a2b1c9d8e7'
down_revision: Union[str, Sequence[str], None] = '39b10c768130'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'few_shot_entries',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('source_ai', sa.String(length=50), server_default='rain', nullable=False,
                  comment='AI tool that generated this entry: rain, claude, claude_code, etc.'),
        sa.Column('query_pattern', sa.Text(), nullable=False,
                  comment='Generalized query pattern — gets embedded for semantic retrieval.'),
        sa.Column('response_structure', sa.String(length=500), nullable=False,
                  comment="Brief description of the response structure."),
        sa.Column('response_sample', sa.Text(), nullable=False,
                  comment='Full or trimmed example response.'),
        sa.Column('task_type', sa.String(length=50), server_default='general_chat', nullable=False,
                  comment='Task classification: code, translation, definition, research, creative, general_chat.'),
        sa.Column('domain_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Domain tags: [python, fastapi, architecture, ...].'),
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False,
                  comment='Primary language: en, id, mixed.'),
        sa.Column('complexity', sa.String(length=20), server_default='medium', nullable=False,
                  comment='Complexity tier: simple, medium, complex.'),
        sa.Column('quality_score', sa.Float(), server_default=sa.text('0.8'), nullable=False,
                  comment='Quality score 0.0-1.0. Starts high, adjusted by feedback.'),
        sa.Column('times_used', sa.Integer(), server_default=sa.text('0'), nullable=False,
                  comment='How many times this example was retrieved and injected.'),
        sa.Column('was_helpful', sa.Boolean(), nullable=True,
                  comment='Explicit user feedback: True=helpful, False=not helpful, None=no feedback yet.'),
        sa.Column('estimated_tokens', sa.Integer(), server_default=sa.text('0'), nullable=False,
                  comment='Rough token count of response_sample (4 chars ≈ 1 token).'),
        sa.Column('id', sa.Uuid(), nullable=False, comment='Primary key (UUIDv4).'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False, comment='Row creation time (UTC).'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False, comment='Last modification time (UTC).'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_few_shot_entries_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_few_shot_entries')),
        comment='Curated query-response pairs for cross-AI few-shot learning.',
    )
    op.create_index(op.f('ix_few_shot_entries_user_id'), 'few_shot_entries', ['user_id'])
    op.create_index(op.f('ix_few_shot_entries_task_type'), 'few_shot_entries', ['task_type'])
    op.create_index(op.f('ix_few_shot_entries_language'), 'few_shot_entries', ['language'])
    op.create_index(op.f('ix_few_shot_entries_quality_score'), 'few_shot_entries', ['quality_score'])

    op.create_table(
        'session_states',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('session_key', sa.String(length=100), nullable=False,
                  comment="Short slug identifying this session."),
        sa.Column('source_ai', sa.String(length=50), server_default='rain', nullable=False,
                  comment='AI tool that last wrote this state: rain, claude, claude_code, etc.'),
        sa.Column('context_summary', sa.Text(), nullable=False,
                  comment='Dense summary of what was accomplished this session.'),
        sa.Column('active_task', sa.Text(), nullable=True,
                  comment='Current in-progress task description, if any.'),
        sa.Column('key_decisions', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='List of key decisions made: [{decision, rationale}].'),
        sa.Column('next_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Ordered list of next steps for the receiving AI.'),
        sa.Column('artifacts', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Key artifacts produced: {files: [], urls: [], code_snippets: []}.'),
        sa.Column('hand_off_to', sa.String(length=50), nullable=True,
                  comment='Target AI for handoff: claude, claude_code, rain_storm, etc.'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False,
                  comment='Whether this is the current active session for the user.'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Optional TTL — NULL means no expiry.'),
        sa.Column('id', sa.Uuid(), nullable=False, comment='Primary key (UUIDv4).'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False, comment='Row creation time (UTC).'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False, comment='Last modification time (UTC).'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_session_states_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_session_states')),
        comment='Cross-AI session state registry for seamless handoffs.',
    )
    op.create_index(op.f('ix_session_states_user_id'), 'session_states', ['user_id'])
    op.create_index(op.f('ix_session_states_is_active'), 'session_states', ['is_active'])
    op.create_index(op.f('ix_session_states_session_key'), 'session_states', ['session_key'])


def downgrade() -> None:
    op.drop_index(op.f('ix_session_states_session_key'), table_name='session_states')
    op.drop_index(op.f('ix_session_states_is_active'), table_name='session_states')
    op.drop_index(op.f('ix_session_states_user_id'), table_name='session_states')
    op.drop_table('session_states')

    op.drop_index(op.f('ix_few_shot_entries_quality_score'), table_name='few_shot_entries')
    op.drop_index(op.f('ix_few_shot_entries_language'), table_name='few_shot_entries')
    op.drop_index(op.f('ix_few_shot_entries_task_type'), table_name='few_shot_entries')
    op.drop_index(op.f('ix_few_shot_entries_user_id'), table_name='few_shot_entries')
    op.drop_table('few_shot_entries')
