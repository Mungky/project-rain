from uuid import UUID
from datetime import datetime
from sqlalchemy import ForeignKey, Index, String, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin

class Conversation(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    """A user's chat session. Holds an ordered list of messages."""

    __tablename__ = "conversations"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owner user.",
    )
    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="User-provided or auto-generated title.",
    )
    persona: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="drizzle",
        comment="Active persona: drizzle (chat/tools), nimbus (generative), shower (quick-reply), or storm (orchestrator).",
    )
    auto_skills: Mapped[bool] = mapped_column(
        nullable=False,
        server_default="true",
        comment="If true, AI chooses skills automatically.",
    )
    enabled_skills: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment="List of skill names/IDs enabled manually when auto_skills is false.",
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    user: Mapped["User"] = relationship(back_populates="conversations")
    skill_executions: Mapped[list["SkillExecution"]] = relationship(
        back_populates="conversation",
    )

    __table_args__ = (
        Index("ix_conversations_user_id_created_at", "user_id", "created_at"),
        {"comment": "User chat sessions. Soft-deleted via deleted_at."},
    )
