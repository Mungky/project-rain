"""Add tags to model_capability_overrides and model to messages

Revision ID: h3i4j5k6l7m8
Revises: f1a2b3c4d5e6
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'h3i4j5k6l7m8'
down_revision: Union[str, Sequence[str], None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'model_capability_overrides',
        sa.Column(
            'tags',
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Task-type tags used for model rotation.",
        ),
    )
    op.add_column(
        'messages',
        sa.Column(
            'model',
            sa.String(200),
            nullable=True,
            comment="Model that generated this message.",
        ),
    )


def downgrade() -> None:
    op.drop_column('model_capability_overrides', 'tags')
    op.drop_column('messages', 'model')
