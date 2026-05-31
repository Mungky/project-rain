from uuid import UUID
from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin

class UserPreference(Base, UUIDPKMixin, TimestampMixin):
    """User-specific settings and preferences."""

    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="Owner user.",
    )
    custom_system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Global instructions like 'Always be concise'.",
    )
    user_context: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Facts about the user like 'I prefer Next.js'.",
    )
    api_keys: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=text("'{}'::jsonb"),
        comment="Encrypted/raw API keys for hosted providers.",
    )
    custom_modes: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=text("'[]'::jsonb"),
        comment="User-defined behavior modes: [{key,label,directive}].",
    )

    user: Mapped["User"] = relationship(back_populates="preference")

    __table_args__ = (
        {"comment": "User-defined agent instructions and preferences."},
    )
