"""Pydantic DTOs for skill API endpoints."""

from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator
from .dto_common import UTCDatetime


class Skill(BaseModel):
    """Skill response model."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    description: str | None = None
    enabled: bool
    manifest_json: dict[str, Any]
    created_at: UTCDatetime
    updated_at: UTCDatetime

    @field_validator("description", mode="before")
    @classmethod
    def extract_description(cls, v: Any, info: Any) -> Any:
        if v:
            return v
        return v


class SkillListResponse(BaseModel):
    """List of skills response."""
    skills: list[Skill]
    total_count: int


class InstallSkillRequest(BaseModel):
    """Request to install a new skill via Git."""
    git_url: str
