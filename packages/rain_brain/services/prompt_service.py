"""Service layer for prompt management."""

from uuid import UUID
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas.prompt import Prompt as PromptModel
from db.schemas.model_capability_override import ModelCapabilityOverride as OverrideModel
from db.schemas.dto_prompt import Prompt, ModelCapabilityOverride


class PromptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_prompts(self) -> list[Prompt]:
        result = await self.db.execute(select(PromptModel).order_by(PromptModel.name))
        return [Prompt.model_validate(p) for p in result.scalars().all()]

    async def get_prompt(self, prompt_id: UUID) -> Prompt | None:
        result = await self.db.execute(select(PromptModel).where(PromptModel.id == prompt_id))
        p = result.scalar_one_or_none()
        return Prompt.model_validate(p) if p else None

    async def get_default_prompt(self) -> Prompt | None:
        result = await self.db.execute(
            select(PromptModel).where(PromptModel.is_default == True).limit(1)
        )
        p = result.scalar_one_or_none()
        return Prompt.model_validate(p) if p else None

    async def create_prompt(self, name: str, content: str, description: str | None = None,
                            category: str | None = None, is_default: bool = False) -> Prompt:
        if is_default:
            await self._clear_default()
        p = PromptModel(name=name, content=content, description=description,
                        category=category, is_default=is_default)
        self.db.add(p)
        await self.db.commit()
        await self.db.refresh(p)
        return Prompt.model_validate(p)

    async def update_prompt(self, prompt_id: UUID, **kwargs) -> Prompt | None:
        result = await self.db.execute(select(PromptModel).where(PromptModel.id == prompt_id))
        p = result.scalar_one_or_none()
        if not p:
            return None
        if kwargs.get("is_default"):
            await self._clear_default()
        for k, v in kwargs.items():
            if v is not None:
                setattr(p, k, v)
        p.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(p)
        return Prompt.model_validate(p)

    async def delete_prompt(self, prompt_id: UUID) -> bool:
        result = await self.db.execute(select(PromptModel).where(PromptModel.id == prompt_id))
        p = result.scalar_one_or_none()
        if not p:
            return False
        await self.db.delete(p)
        await self.db.commit()
        return True

    async def _clear_default(self):
        result = await self.db.execute(select(PromptModel).where(PromptModel.is_default == True))
        for p in result.scalars().all():
            p.is_default = False


class ModelCapabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_overrides(self) -> list[ModelCapabilityOverride]:
        result = await self.db.execute(select(OverrideModel).order_by(OverrideModel.model_id))
        return [ModelCapabilityOverride.model_validate(o) for o in result.scalars().all()]

    async def get_override(self, model_id: str) -> ModelCapabilityOverride | None:
        result = await self.db.execute(
            select(OverrideModel).where(OverrideModel.model_id == model_id)
        )
        o = result.scalar_one_or_none()
        return ModelCapabilityOverride.model_validate(o) if o else None

    # Auto-derived capabilities for each persona
    _PERSONA_CAPS: dict[str, list[str]] = {
        "drizzle": ["chat", "tools"],
        "nimbus":  ["image-gen"],
        "shower":  ["chat"],
        "storm":   ["chat", "tools", "vision", "thinking", "image-gen"],
    }

    async def upsert(
        self,
        model_id: str,
        capabilities: list[str] | None = None,
        tags: list[str] | None = None,
        display_name: str | None = None,
        notes: str | None = None,
        persona: str = "drizzle",
    ) -> ModelCapabilityOverride:
        resolved_caps = capabilities if capabilities else self._PERSONA_CAPS.get(persona, ["chat"])
        result = await self.db.execute(
            select(OverrideModel).where(OverrideModel.model_id == model_id)
        )
        o = result.scalar_one_or_none()
        if o:
            o.capabilities = resolved_caps
            o.persona = persona
            if tags is not None:
                o.tags = tags
            if display_name is not None:
                o.display_name = display_name
            if notes is not None:
                o.notes = notes
            o.updated_at = datetime.now(UTC)
        else:
            o = OverrideModel(
                model_id=model_id,
                capabilities=resolved_caps,
                tags=tags or [],
                display_name=display_name,
                notes=notes,
                persona=persona,
            )
            self.db.add(o)
        await self.db.commit()
        await self.db.refresh(o)
        return ModelCapabilityOverride.model_validate(o)

    async def delete_override(self, model_id: str) -> bool:
        result = await self.db.execute(
            select(OverrideModel).where(OverrideModel.model_id == model_id)
        )
        o = result.scalar_one_or_none()
        if not o:
            return False
        await self.db.delete(o)
        await self.db.commit()
        return True
