"""Prompt management endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from rain_backend.api.deps import get_db
from rain_brain.services.prompt_service import PromptService, ModelCapabilityService
from db.schemas.dto_prompt import (
    Prompt, CreatePromptRequest, UpdatePromptRequest,
    ModelCapabilityOverride, UpsertModelCapabilitiesRequest,
)

router = APIRouter()


# ── Model Capability Overrides ─────────────────────────────────────────────────

@router.get("/model-capabilities", response_model=list[ModelCapabilityOverride])
async def list_model_capabilities(
    db: AsyncSession = Depends(get_db),
) -> list[ModelCapabilityOverride]:
    return await ModelCapabilityService(db).list_overrides()


@router.put("/model-capabilities/{model_id}", response_model=ModelCapabilityOverride)
async def upsert_model_capabilities(
    model_id: str,
    body: UpsertModelCapabilitiesRequest,
    db: AsyncSession = Depends(get_db),
) -> ModelCapabilityOverride:
    return await ModelCapabilityService(db).upsert(
        model_id=model_id,
        capabilities=body.capabilities or None,
        tags=body.tags or None,
        display_name=body.display_name,
        notes=body.notes,
        persona=body.persona,
    )


@router.delete("/model-capabilities/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_capabilities(
    model_id: str, db: AsyncSession = Depends(get_db)
) -> None:
    deleted = await ModelCapabilityService(db).delete_override(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No override found for this model")


# ── Prompts ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[Prompt])
async def list_prompts(db: AsyncSession = Depends(get_db)) -> list[Prompt]:
    return await PromptService(db).list_prompts()


@router.post("", response_model=Prompt, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    body: CreatePromptRequest, db: AsyncSession = Depends(get_db)
) -> Prompt:
    return await PromptService(db).create_prompt(
        name=body.name, content=body.content, description=body.description,
        category=body.category, is_default=body.is_default,
    )


@router.get("/{prompt_id}", response_model=Prompt)
async def get_prompt(prompt_id: UUID, db: AsyncSession = Depends(get_db)) -> Prompt:
    p = await PromptService(db).get_prompt(prompt_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return p


@router.patch("/{prompt_id}", response_model=Prompt)
async def update_prompt(
    prompt_id: UUID, body: UpdatePromptRequest, db: AsyncSession = Depends(get_db)
) -> Prompt:
    p = await PromptService(db).update_prompt(
        prompt_id, **body.model_dump(exclude_none=True)
    )
    if not p:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return p


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(prompt_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    deleted = await PromptService(db).delete_prompt(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prompt not found")
