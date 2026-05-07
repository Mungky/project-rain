from uuid import UUID
from datetime import datetime
from sqlalchemy import ForeignKey, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDPKMixin, TimestampMixin


class NimbusDocument(Base, UUIDPKMixin, TimestampMixin):
    """File arsip yang dikelola oleh Nimbus agent."""

    __tablename__ = "nimbus_documents"

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    archived_filename: Mapped[str] = mapped_column(String(500), nullable=False)

    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    client_code: Mapped[str] = mapped_column(String(50), nullable=False)
    project_code: Mapped[str] = mapped_column(String(50), nullable=False)
    folder_category: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[str] = mapped_column(String(10), nullable=False, default="V1")

    drive_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    drive_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")

    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Temporary access link token (32-byte hex → 64 chars)
    access_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
