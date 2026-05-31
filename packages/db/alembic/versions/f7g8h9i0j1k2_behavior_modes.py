"""Add behavior_mode to conversations and custom_modes to user_preferences.

Revision ID: f7g8h9i0j1k2
Revises: e5f6a7b8c9d0
Create Date: 2026-05-31 00:00:00.000000

Idempotent: checks for existing columns before adding so re-running against a
bootstrapped database is safe.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f7g8h9i0j1k2"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _has_column("conversations", "behavior_mode"):
        op.add_column(
            "conversations",
            sa.Column(
                "behavior_mode",
                sa.String(40),
                nullable=True,
                comment=(
                    "Behavioral stance key (built-in: discussion/teacher/mentor/friend, "
                    "or a custom mode key). Null/default = persona default."
                ),
            ),
        )
    if not _has_column("user_preferences", "custom_modes"):
        op.add_column(
            "user_preferences",
            sa.Column(
                "custom_modes",
                JSONB,
                nullable=True,
                server_default=sa.text("'[]'::jsonb"),
                comment="User-defined behavior modes: [{key,label,directive}].",
            ),
        )


def downgrade() -> None:
    if _has_column("user_preferences", "custom_modes"):
        op.drop_column("user_preferences", "custom_modes")
    if _has_column("conversations", "behavior_mode"):
        op.drop_column("conversations", "behavior_mode")
