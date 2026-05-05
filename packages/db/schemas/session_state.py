from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey, Index, String, Text, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDPKMixin, TimestampMixin


class SessionState(Base, UUIDPKMixin, TimestampMixin):
    """Cross-AI session state for seamless handoffs between AI tools."""

    __tablename__ = "session_states"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owner user.",
    )
    session_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Short slug identifying this session (e.g. 'rain-drizzle-2026-05-05').",
    )
    source_ai: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="rain",
        comment="AI tool that last wrote this state: rain, claude, claude_code, etc.",
    )
    context_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Dense summary of what was accomplished this session.",
    )
    active_task: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Current in-progress task description, if any.",
    )
    key_decisions: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of key decisions made: [{decision, rationale}].",
    )
    next_steps: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Ordered list of next steps for the receiving AI.",
    )
    artifacts: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Key artifacts produced: {files: [], urls: [], code_snippets: []}.",
    )
    hand_off_to: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Target AI for handoff: claude, claude_code, rain_storm, etc.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        comment="Whether this is the current active session for the user.",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional TTL — NULL means no expiry.",
    )

    __table_args__ = (
        Index("ix_session_states_user_id", "user_id"),
        Index("ix_session_states_is_active", "is_active"),
        Index("ix_session_states_session_key", "session_key"),
        {"comment": "Cross-AI session state registry for seamless handoffs."},
    )
