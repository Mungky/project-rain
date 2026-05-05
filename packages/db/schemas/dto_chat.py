"""Pydantic DTOs for chat streaming endpoints."""

from uuid import UUID
from pydantic import BaseModel, Field


class AttachmentItem(BaseModel):
    name: str
    content: str  # base64 for images, raw text for text files
    mime_type: str = "text/plain"


class PostMessageRequest(BaseModel):
    """Request to post a new message to a conversation."""
    content: str = Field(default="", max_length=100000)
    model: str | None = Field(
        default=None,
        description="LLM model to use for response. If None, uses conversation's model.",
    )
    attachments: list[AttachmentItem] | None = None
