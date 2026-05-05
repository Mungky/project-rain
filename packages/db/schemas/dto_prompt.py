"""Pydantic DTOs for prompt management."""

from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .dto_common import UTCDatetime


class Prompt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    content: str
    category: str | None = None
    is_default: bool = False
    created_at: UTCDatetime
    updated_at: UTCDatetime


class CreatePromptRequest(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = None
    content: str = Field(min_length=1)
    category: str | None = Field(default=None, max_length=100)
    is_default: bool = False


class UpdatePromptRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    content: str | None = None
    category: str | None = Field(default=None, max_length=100)
    is_default: bool | None = None


class ModelCapabilityOverride(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: str
    display_name: str | None = None
    capabilities: list[str] = []
    tags: list[str] = []
    notes: str | None = None
    persona: str = "drizzle"

    @field_validator("capabilities", "tags", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        return v if v is not None else []


class UpsertModelCapabilitiesRequest(BaseModel):
    capabilities: list[str] = Field(default_factory=list,
        description="Leave empty to auto-derive from persona.")
    tags: list[str] = Field(default_factory=list,
        description="Task-type tags: default, vision, coding, math, creative_writing, etc.")
    display_name: str | None = None
    notes: str | None = None
    persona: str = "drizzle"
