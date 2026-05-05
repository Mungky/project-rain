"""add_feedback_and_reasoning_to_messages

Revision ID: 3c737a5a064e
Revises: 3c737a5a064d
Create Date: 2026-04-23 10:00:00.000000

Backend ref: WO-022
PRD/CONTRACTS: Contract 3 (Postgres)

Reason: UI/UX polish — persist user thumbs-up/down feedback on messages
and store model reasoning/thinking content (or RAG context summaries)
for audit and display.

Safety:
- Both columns are nullable; safe on populated DB.
- No data backfill needed (NULL = no feedback / no reasoning).
- Downgrade simply drops both columns. No data loss concern (analytics-only).
"""
from alembic import op
import sqlalchemy as sa


revision = "3c737a5a064e"
down_revision = "3c737a5a064d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "feedback",
            sa.Integer(),
            nullable=True,
            comment="User feedback rating: 1 = thumbs up, -1 = thumbs down, NULL = none.",
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "reasoning_content",
            sa.Text(),
            nullable=True,
            comment="Model reasoning/thinking content or RAG context summary.",
        ),
    )
    op.execute("COMMENT ON COLUMN messages.feedback IS 'User feedback rating: 1 = thumbs up, -1 = thumbs down, NULL = none.'")
    op.execute("COMMENT ON COLUMN messages.reasoning_content IS 'Model reasoning/thinking content or RAG context summary.'")


def downgrade() -> None:
    op.drop_column("messages", "reasoning_content")
    op.drop_column("messages", "feedback")