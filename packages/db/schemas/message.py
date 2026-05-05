from uuid import UUID
import enum
from sqlalchemy import ForeignKey, Index, Integer, String, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin

class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"

class Message(Base, UUIDPKMixin, TimestampMixin):
    """A single turn in a conversation."""

    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent conversation.",
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", create_constraint=True),
        nullable=False,
        comment="Sender role.",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The actual text content of the message.",
    )
    tokens_in: Mapped[int] = mapped_column(
        nullable=False,
        server_default="0",
        comment="Prompt token count.",
    )
    tokens_out: Mapped[int] = mapped_column(
        nullable=False,
        server_default="0",
        comment="Completion token count.",
    )
    feedback: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="User feedback rating: 1 = thumbs up, -1 = thumbs down, NULL = none.",
    )
    reasoning_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Model reasoning/thinking content or RAG context summary.",
    )
    attachments: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of {id, filename, mime} for files/images saved to Neural Archive.",
    )
    model: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Model that generated this message (assistant only). Tracks per-message model rotation.",
    )
    tool_events: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tool calls made during this message: [{name, args, result, status}].",
    )
    react_steps: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="ReAct iteration summaries: [{iteration, tools: [{name, arg_preview}]}].",
    )
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"),
        {"comment": "Individual messages within a conversation."},
    )
