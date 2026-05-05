from uuid import UUID
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin

class User(Base, UUIDPKMixin, TimestampMixin):
    """The system user. In Phase 1, this typically handles a single default user."""
    
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Unique identifier for the user account.",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User email address.",
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
        {"comment": "System users. Primary identity for data ownership."},
    )
