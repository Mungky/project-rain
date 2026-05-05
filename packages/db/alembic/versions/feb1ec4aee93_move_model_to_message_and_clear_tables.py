"""move_model_to_message_and_clear_tables

Revision ID: feb1ec4aee93
Revises: h3i4j5k6l7m8
Create Date: 2026-04-27 01:29:03.246449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'feb1ec4aee93'
down_revision: Union[str, Sequence[str], None] = 'h3i4j5k6l7m8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Clear tables as requested
    op.execute("TRUNCATE TABLE messages CASCADE")
    op.execute("TRUNCATE TABLE conversations CASCADE")
    
    # 2. Drop model column from conversations
    op.drop_column('conversations', 'model')


def downgrade() -> None:
    # Add column back with a default
    op.add_column('conversations', sa.Column('model', sa.String(100), nullable=False, server_default='kimi-k2.6:cloud'))
