from uuid import UUID
from sqlalchemy import ForeignKey, Index, String, Text, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDPKMixin, TimestampMixin


class ContextEntry(Base, UUIDPKMixin, TimestampMixin):
    """A user-defined knowledge fragment stored in the context library (RAG source)."""

    __tablename__ = "context_entries"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owner user.",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Short label shown in the UI.",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The full text that gets embedded and retrieved.",
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Top-level category, e.g. 'Brand', 'Market', 'Product'.",
    )
    subcategory: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Sub-category, e.g. 'Voice', 'Audience'.",
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="manual",
        comment="Origin: manual | session | archive.",
    )
    source_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="conversation_id or document_id when auto-extracted.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        comment="If false, excluded from RAG retrieval.",
    )

    __table_args__ = (
        Index("ix_context_entries_user_id", "user_id"),
        Index("ix_context_entries_category", "category"),
        {"comment": "User knowledge fragments for RAG retrieval."},
    )
