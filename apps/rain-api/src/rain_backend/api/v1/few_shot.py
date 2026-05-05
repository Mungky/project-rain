"""Few-Shot Library API endpoints."""

import logging
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from rain_backend.api.deps import get_db, get_qdrant, get_providers
from rain_brain.services.few_shot_service import FewShotService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class FewShotEntryResponse(BaseModel):
    id: str
    source_ai: str
    query_pattern: str
    response_structure: str
    response_sample: str
    task_type: str
    domain_tags: list[str]
    language: str
    complexity: str
    quality_score: float
    times_used: int
    was_helpful: bool | None
    estimated_tokens: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SavePatternBody(BaseModel):
    query_pattern: str = Field(..., min_length=5, description="Generalized query pattern to embed.")
    response_structure: str = Field(..., max_length=500, description="Brief description of response structure.")
    response_sample: str = Field(..., min_length=10, description="Full or trimmed example response.")
    task_type: Literal["code", "translation", "definition", "research", "creative", "general_chat"] = "general_chat"
    domain_tags: list[str] = []
    language: Literal["en", "id", "mixed"] = "en"
    complexity: Literal["simple", "medium", "complex"] = "medium"
    source_ai: str = "rain"
    quality_score: float = Field(default=0.8, ge=0.0, le=1.0)


class FeedbackBody(BaseModel):
    helpful: bool


class SemanticSearchBody(BaseModel):
    query: str = Field(..., min_length=3)
    task_type: str | None = None
    language: str | None = None
    limit: int = Field(default=3, ge=1, le=10)
    min_quality: float = Field(default=0.7, ge=0.0, le=1.0)


class SemanticSearchResult(BaseModel):
    id: str
    query_pattern: str
    response_structure: str
    response_sample: str
    task_type: str
    language: str
    quality_score: float
    score: float


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[FewShotEntryResponse])
async def list_few_shot_entries(
    task_type: str | None = Query(None),
    language: str | None = Query(None),
    min_quality: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[FewShotEntryResponse]:
    service = FewShotService(db)
    entries = await service.list_entries(
        task_type=task_type,
        language=language,
        min_quality=min_quality,
        limit=limit,
    )
    return [_to_response(e) for e in entries]


@router.post("", response_model=FewShotEntryResponse, status_code=status.HTTP_201_CREATED)
async def save_pattern(
    body: SavePatternBody,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
    providers: dict = Depends(get_providers),
) -> FewShotEntryResponse:
    service = FewShotService(db)
    ollama = providers.get("ollama")
    entry = await service.save_pattern(
        query_pattern=body.query_pattern,
        response_structure=body.response_structure,
        response_sample=body.response_sample,
        task_type=body.task_type,
        domain_tags=body.domain_tags,
        language=body.language,
        complexity=body.complexity,
        source_ai=body.source_ai,
        quality_score=body.quality_score,
        qdrant_client=qdrant_client,
        embed_provider=ollama,
    )
    return _to_response(entry)


@router.post("/search", response_model=list[SemanticSearchResult])
async def semantic_search(
    body: SemanticSearchBody,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
    providers: dict = Depends(get_providers),
) -> list[SemanticSearchResult]:
    """Retrieve semantically similar few-shot examples for a given query."""
    ollama = providers.get("ollama")
    if not ollama or not qdrant_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_unavailable", "message": "Embedding provider or Qdrant not available."},
        )
    service = FewShotService(db)
    results = await service.semantic_search(
        query=body.query,
        embed_provider=ollama,
        qdrant_client=qdrant_client,
        task_type=body.task_type,
        language=body.language,
        limit=body.limit,
        min_quality=body.min_quality,
    )
    return [SemanticSearchResult(**r) for r in results]


@router.post("/{entry_id}/feedback", response_model=FewShotEntryResponse)
async def submit_feedback(
    entry_id: UUID,
    body: FeedbackBody,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
) -> FewShotEntryResponse:
    """Mark a few-shot example as helpful or not. Adjusts quality score and syncs to Qdrant."""
    service = FewShotService(db)
    entry = await service.mark_helpful(entry_id=entry_id, helpful=body.helpful, qdrant_client=qdrant_client)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Few-shot entry not found."},
        )
    return _to_response(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
) -> None:
    service = FewShotService(db)
    success = await service.delete_entry(entry_id=entry_id, qdrant_client=qdrant_client)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Few-shot entry not found."},
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(entry) -> FewShotEntryResponse:
    return FewShotEntryResponse(
        id=str(entry.id),
        source_ai=entry.source_ai,
        query_pattern=entry.query_pattern,
        response_structure=entry.response_structure,
        response_sample=entry.response_sample,
        task_type=entry.task_type,
        domain_tags=entry.domain_tags or [],
        language=entry.language,
        complexity=entry.complexity,
        quality_score=entry.quality_score,
        times_used=entry.times_used,
        was_helpful=entry.was_helpful,
        estimated_tokens=entry.estimated_tokens,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )
