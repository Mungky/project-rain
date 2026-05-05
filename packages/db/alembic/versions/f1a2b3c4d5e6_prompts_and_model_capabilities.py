"""prompts_and_model_capabilities

Revision ID: f1a2b3c4d5e6
Revises: d4f7c8e9a1b2
Create Date: 2026-04-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'd4f7c8e9a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'prompts',
        sa.Column('id', sa.Uuid(), nullable=False, comment='Primary key (UUIDv4).'),
        sa.Column('name', sa.String(200), nullable=False, comment='Display name for the prompt.'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional description shown in the prompt library.'),
        sa.Column('content', sa.Text(), nullable=False, comment='The system prompt text.'),
        sa.Column('category', sa.String(100), nullable=True, comment='Optional grouping label.'),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False,
                  comment='If true, this prompt is used as the default system prompt.'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='Saved system prompt templates.',
    )
    op.create_index('ix_prompts_is_default', 'prompts', ['is_default'])

    op.create_table(
        'model_capability_overrides',
        sa.Column('model_id', sa.String(200), primary_key=True,
                  comment="Model identifier, e.g. 'llava:7b' or 'mistral:latest'."),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'[]'"),
                  comment='List of capability strings: chat, tools, vision, thinking, image-gen.'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Optional freeform notes about the model.'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        comment='User-defined capability tags for models (primarily Ollama local models).',
    )


def downgrade() -> None:
    op.drop_table('model_capability_overrides')
    op.drop_index('ix_prompts_is_default', table_name='prompts')
    op.drop_table('prompts')
