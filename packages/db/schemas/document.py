import enum
from uuid import UUID
from sqlalchemy import ForeignKey, Index, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin


class DocumentStatus(str, enum.Enum):
    uploading = "uploading"
    processing = "processing"
    ready = "ready"
    error = "error"


class Document(Base, UUIDPKMixin, TimestampMixin):
    """A user-uploaded document tracked in Postgres; raw file stored in MinIO, vectors in Qdrant."""

    __tablename__ = "documents"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner user.",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename as uploaded.",
    )
    mime: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="MIME type of the uploaded file.",
    )
    minio_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Object key in MinIO bucket (rain-uploads).",
    )
    qdrant_collection: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default="documents",
        comment="Qdrant collection name where chunks are stored.",
    )
    source_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="manual",
        comment="'manual' = uploaded via Neural Archive UI; 'chat' = auto-saved from chat attachment.",
    )
    message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Original message this attachment came from (chat source only).",
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", create_constraint=True),
        nullable=False,
        server_default="uploading",
        comment="Processing status: uploading → processing → ready | error.",
    )

    user: Mapped["User"] = relationship(back_populates="documents")

    __table_args__ = (
        Index("ix_documents_user_id_created_at", "user_id", "created_at"),
        Index("ix_documents_status", "status"),
        {"comment": "User-uploaded documents. Raw files in MinIO, vectors in Qdrant."},
    )