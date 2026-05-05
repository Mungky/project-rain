from sqlalchemy import String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class ModelCapabilityOverride(Base, TimestampMixin):
    """User-defined capability tags for models (primarily Ollama local models)."""

    __tablename__ = "model_capability_overrides"

    model_id: Mapped[str] = mapped_column(
        String(200), primary_key=True,
        comment="Model identifier, e.g. 'llava:7b' or 'mistral:latest'."
    )
    capabilities: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'"),
        comment="List of capability strings: chat, tools, vision, thinking, image-gen."
    )
    display_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Optional human-friendly label shown in the UI instead of model_id."
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional freeform notes about the model."
    )
    persona: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="drizzle",
        comment="Persona category: drizzle (chat/tools), nimbus (generative), shower (quick-reply), or storm (orchestrator).",
    )
    tags: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'"),
        comment="Task-type tags: default, vision, coding, math, creative_writing, etc. Used for model rotation.",
    )
