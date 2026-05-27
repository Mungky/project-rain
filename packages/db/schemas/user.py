from uuid import UUID
from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin

class User(Base, UUIDPKMixin, TimestampMixin):
    """System user — single-user mode for Rain personal assistant."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Unique identifier for the user account.",
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    preference: Mapped["UserPreference"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        Index("ix_users_username", "username"),
        {"comment": "System user for Rain personal assistant (single-user mode)."},
    )