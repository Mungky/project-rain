from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDPKMixin, TimestampMixin


class Prompt(Base, UUIDPKMixin, TimestampMixin):
    """Saved system prompt templates."""

    __tablename__ = "prompts"

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Display name for the prompt."
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional description shown in the prompt library."
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="The system prompt text."
    )
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Optional grouping label."
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False,
        comment="If true, this prompt is used as the default system prompt."
    )
