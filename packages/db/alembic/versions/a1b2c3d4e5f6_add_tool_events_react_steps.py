"""add_tool_events_and_react_steps_to_messages

Revision ID: a1b2c3d4e5f6
Revises: feb1ec4aee93
Create Date: 2026-04-27 12:00:00.000000

Reason: Persist tool call events and ReAct iteration summaries so the
frontend ThinkingBlock survives a query invalidation after streaming ends.

Safety:
- Both columns are nullable JSONB; safe on populated DB.
- No data backfill needed (NULL = no tool events / no ReAct steps).
- Downgrade simply drops both columns.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "a1b2c3d4e5f6"
down_revision = "feb1ec4aee93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "tool_events",
            JSONB,
            nullable=True,
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "react_steps",
            JSONB,
            nullable=True,
        ),
    )
    op.execute(
        "COMMENT ON COLUMN messages.tool_events "
        "IS 'Tool calls made during this message: [{name, args, result, status}].'"
    )
    op.execute(
        "COMMENT ON COLUMN messages.react_steps "
        "IS 'ReAct iteration summaries: [{iteration, tools: [{name, arg_preview}]}].'"
    )


def downgrade() -> None:
    op.drop_column("messages", "react_steps")
    op.drop_column("messages", "tool_events")