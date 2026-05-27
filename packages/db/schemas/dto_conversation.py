"""Pydantic DTOs for conversation API endpoints."""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .message import MessageRole
from .dto_common import UTCDatetime


class MessageAttachment(BaseModel):
    """Metadata for a file/image saved to Neural Archive from a chat message."""
    id: str
    filename: str
    mime: str


class ToolEventSchema(BaseModel):
    """A single tool call event within a message."""
    name: str
    args: dict | None = None
    result: object | None = None
    status: Literal["calling", "done"] = "done"


class ReactStepSchema(BaseModel):
    """A ReAct iteration summary within a message."""
    iteration: int
    tools: list[dict] = Field(default_factory=list)


class Message(BaseModel):
    """Message in a conversation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    reasoning_content: str | None = None
    tool_events: list[ToolEventSchema] | None = None
    react_steps: list[ReactStepSchema] | None = None
    feedback: int | None = Field(default=None, ge=-1, le=1)
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    model: str | None = None
    attachments: list[MessageAttachment] = Field(default_factory=list)
    created_at: UTCDatetime

    @field_validator("attachments", mode="before")
    @classmethod
    def _coerce_attachments(cls, v):
        return v if v is not None else []

    @field_validator("tool_events", mode="before")
    @classmethod
    def _coerce_tool_events(cls, v):
        return v if v is not None else None

    @field_validator("react_steps", mode="before")
    @classmethod
    def _coerce_react_steps(cls, v):
        return v if v is not None else None


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    title: str | None = Field(default=None, max_length=200)
    persona: Literal["drizzle", "shower", "storm"] = "drizzle"


class UpdateConversationRequest(BaseModel):
    """Request to update conversation settings."""
    title: str | None = Field(default=None, max_length=200)
    persona: Literal["drizzle", "shower", "storm"] | None = None
    auto_skills: bool | None = None
    enabled_skills: list[str] | None = None


class MessageFeedbackRequest(BaseModel):
    """Request to update message feedback."""
    feedback: int | None = Field(default=None, ge=-1, le=1)


class ListConversationsQuery(BaseModel):
    """Query parameters for listing conversations."""
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class ConversationPathParams(BaseModel):
    """Path parameters for conversation-specific endpoints."""
    conversation_id: UUID


class Conversation(BaseModel):
    """Conversation response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str | None
    persona: Literal["drizzle", "shower", "storm"] = "drizzle"
    auto_skills: bool = True
    enabled_skills: list[str] = Field(default_factory=list)
    created_at: UTCDatetime
    updated_at: UTCDatetime
    deleted_at: UTCDatetime | None = None


class ConversationResponse(BaseModel):
    """Full conversation response with messages."""
    id: UUID
    user_id: UUID
    title: str | None
    persona: Literal["drizzle", "shower", "storm"] = "drizzle"
    auto_skills: bool = True
    enabled_skills: list[str] = Field(default_factory=list)
    created_at: UTCDatetime
    updated_at: UTCDatetime
    deleted_at: UTCDatetime | None = None
    messages: list[Message] = Field(default_factory=list)


class ConversationCreatedResponse(BaseModel):
    """Response when creating a conversation."""
    id: UUID
    created_at: UTCDatetime


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""
    conversations: list[Conversation]
    total_count: int
    next_cursor: str | None = None
