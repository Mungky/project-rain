"""Pydantic DTOs for document API endpoints."""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from .dto_common import UTCDatetime


DocumentStatusLiteral = Literal["uploading", "processing", "ready", "error"]


class DocumentUploadResponse(BaseModel):
    """Response for POST /v1/documents."""
    id: UUID
    filename: str
    mime: str
    status: DocumentStatusLiteral
    chunk_count: int = Field(default=0, ge=0)
    created_at: UTCDatetime


class DocumentResponse(BaseModel):
    """Full document response for GET endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    filename: str
    mime: str
    minio_key: str
    qdrant_collection: str
    source_type: str = "manual"
    message_id: UUID | None = None
    status: DocumentStatusLiteral
    created_at: UTCDatetime
    updated_at: UTCDatetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: list[DocumentResponse]
    total_count: int
