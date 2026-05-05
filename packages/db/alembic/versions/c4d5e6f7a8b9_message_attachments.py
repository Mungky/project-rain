"""Add message attachments and document source tracking.

Revision ID: c4d5e6f7a8b9
Revises: a2b3c4d5e6f7
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c4d5e6f7a8b9"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # messages.attachments — stores [{id, filename, mime}] for chat file saves
    op.add_column(
        "messages",
        sa.Column("attachments", postgresql.JSONB(), nullable=True,
                  comment="List of {id, filename, mime} for files/images saved to Neural Archive."),
    )

    # documents.source_type — 'manual' (UI upload) or 'chat' (from message)
    op.add_column(
        "documents",
        sa.Column("source_type", sa.String(16), nullable=False,
                  server_default="manual",
                  comment="'manual' = Neural Archive UI; 'chat' = auto-saved from chat attachment."),
    )

    # documents.message_id — optional back-link to originating message
    op.add_column(
        "documents",
        sa.Column("message_id", sa.Uuid(), nullable=True,
                  comment="Original message this attachment came from (chat source only)."),
    )
    op.create_foreign_key(
        "fk_documents_message_id",
        "documents", "messages",
        ["message_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_documents_message_id", "documents", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_message_id", table_name="documents")
    op.drop_constraint("fk_documents_message_id", "documents", type_="foreignkey")
    op.drop_column("documents", "message_id")
    op.drop_column("documents", "source_type")
    op.drop_column("messages", "attachments")
