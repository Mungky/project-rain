from uuid import UUID
from sqlalchemy import ForeignKey, Index, String, Text, Float, Integer, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDPKMixin, TimestampMixin


class FewShotEntry(Base, UUIDPKMixin, TimestampMixin):
    """A curated example pair stored in the Few-Shot Library for cross-AI learning."""

    __tablename__ = "few_shot_entries"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owner user.",
    )
    source_ai: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="rain",
        comment="AI tool that generated this entry: rain, claude, claude_code, etc.",
    )
    query_pattern: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Generalized query pattern — gets embedded for semantic retrieval.",
    )
    response_structure: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Brief description of the response structure (e.g. 'numbered list, code block at end').",
    )
    response_sample: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full or trimmed example response.",
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="general_chat",
        comment="Task classification: code, translation, definition, research, creative, general_chat.",
    )
    domain_tags: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Domain tags: [python, fastapi, architecture, ...].",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="en",
        comment="Primary language: en, id, mixed.",
    )
    complexity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="medium",
        comment="Complexity tier: simple, medium, complex.",
    )
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default=text("0.8"),
        comment="Quality score 0.0-1.0. Starts high, adjusted by feedback.",
    )
    times_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="How many times this example was retrieved and injected.",
    )
    was_helpful: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Explicit user feedback: True=helpful, False=not helpful, None=no feedback yet.",
    )
    estimated_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Rough token count of response_sample (4 chars ≈ 1 token).",
    )

    __table_args__ = (
        Index("ix_few_shot_entries_user_id", "user_id"),
        Index("ix_few_shot_entries_task_type", "task_type"),
        Index("ix_few_shot_entries_language", "language"),
        Index("ix_few_shot_entries_quality_score", "quality_score"),
        {"comment": "Curated query-response pairs for cross-AI few-shot learning."},
    )
