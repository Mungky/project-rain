"""Common Pydantic DTOs shared across all API endpoints."""

from datetime import datetime, UTC
from typing import Annotated, Any
from pydantic import BaseModel, AfterValidator


def _ensure_utc(v: datetime) -> datetime:
    """Convert naive datetimes to UTC-aware. Pass aware datetimes through."""
    if v.tzinfo is None:
        return v.replace(tzinfo=UTC)
    return v


UTCDatetime = Annotated[datetime, AfterValidator(_ensure_utc)]


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    ollama: bool
    postgres: bool
    redis: bool
    qdrant: bool
    minio: bool


class ModelResponse(BaseModel):
    """Model listing response."""
    id: str
    name: str
    display_name: str | None = None
    provider: str
    enabled: bool = True
    capabilities: list[str] = []
