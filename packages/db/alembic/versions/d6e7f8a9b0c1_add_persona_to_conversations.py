"""Add persona column to conversations.

Revision ID: d6e7f8a9b0c1
Revises: c4d5e6f7a8b9
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "persona",
            sa.String(20),
            server_default="drizzle",
            nullable=False,
            comment="Active persona: drizzle (chat/tools) or nimbus (generative).",
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "persona")
