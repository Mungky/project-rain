from uuid import UUID
from datetime import datetime
from sqlalchemy import (
    ForeignKey, Index, Integer, String, Text, Boolean,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin


class Skill(Base, UUIDPKMixin, TimestampMixin):
    """An installed skill registered in the system. Manifest validated against skill_manifest_schema.json."""

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable skill name, e.g. web-search-duckduckgo.",
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Semver string, e.g. 0.1.0.",
    )
    manifest_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full skill manifest, validated against /backend/schemas/skill_manifest.schema.json on insert.",
    )
    docker_image: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Docker image tag for the sandboxed skill runtime.",
    )
    installed_at: Mapped[datetime] = mapped_column(
        server_default="now()",
        nullable=False,
        comment="Timestamp when the skill was installed.",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether the skill is active and available for use.",
    )

    executions: Mapped[list["SkillExecution"]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("uq_skills_name_version", "name", "version", unique=True),
        Index("ix_skills_enabled", "enabled"),
        {"comment": "Installed skills. Manifest stored as JSONB, validated on insert."},
    )


class SkillExecution(Base, UUIDPKMixin, TimestampMixin):
    """A single execution of a skill within a conversation."""

    __tablename__ = "skill_executions"

    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The skill that was executed.",
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Conversation context; NULL if conversation is deleted (preserve audit trail).",
    )
    input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON-encoded input parameters passed to the skill.",
    )
    output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded output from the skill. NULL if execution failed.",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Execution wall-clock time in milliseconds.",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if skill execution failed. NULL on success.",
    )

    skill: Mapped["Skill"] = relationship(back_populates="executions")
    conversation: Mapped["Conversation | None"] = relationship(back_populates="skill_executions")

    __table_args__ = (
        Index("ix_skill_executions_skill_id", "skill_id"),
        Index("ix_skill_executions_conversation_id", "conversation_id"),
        Index("ix_skill_executions_created_at", "created_at"),
        {"comment": "Audit trail of skill executions within conversations."},
    )