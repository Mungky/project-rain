"""Neural Context Library API endpoints."""

import logging
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from rain_backend.api.deps import get_db, get_qdrant, get_providers
from rain_brain.services.context_service import ContextService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ContextEntryResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str | None
    subcategory: str | None
    source_type: str
    source_id: str | None
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CreateContextEntryBody(BaseModel):
    title: str
    content: str
    category: str | None = None
    subcategory: str | None = None
    source_type: Literal["manual", "session", "archive"] = "manual"
    source_id: str | None = None


class UpdateContextEntryBody(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    subcategory: str | None = None
    is_active: bool | None = None


class ExtractFromSessionBody(BaseModel):
    entries: list[CreateContextEntryBody]


class ExtractFromTextBody(BaseModel):
    text: str
    source_type: Literal["manual", "session", "archive"] = "session"
    source_id: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ContextEntryResponse])
async def list_context_entries(
    category: str | None = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
) -> list[ContextEntryResponse]:
    service = ContextService(db)
    entries = await service.list_entries(category=category, active_only=active_only)
    return [
        ContextEntryResponse(
            id=str(e.id),
            title=e.title,
            content=e.content,
            category=e.category,
            subcategory=e.subcategory,
            source_type=e.source_type,
            source_id=e.source_id,
            is_active=e.is_active,
            created_at=e.created_at.isoformat(),
            updated_at=e.updated_at.isoformat(),
        )
        for e in entries
    ]


@router.post("", response_model=ContextEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_context_entry(
    body: CreateContextEntryBody,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
    providers: dict = Depends(get_providers),
) -> ContextEntryResponse:
    service = ContextService(db)
    ollama = providers.get("ollama")
    entry = await service.create_entry(
        title=body.title,
        content=body.content,
        category=body.category,
        subcategory=body.subcategory,
        source_type=body.source_type,
        source_id=body.source_id,
        qdrant_client=qdrant_client,
        embed_provider=ollama,
    )
    return ContextEntryResponse(
        id=str(entry.id),
        title=entry.title,
        content=entry.content,
        category=entry.category,
        subcategory=entry.subcategory,
        source_type=entry.source_type,
        source_id=entry.source_id,
        is_active=entry.is_active,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


@router.put("/{entry_id}", response_model=ContextEntryResponse)
async def update_context_entry(
    entry_id: UUID,
    body: UpdateContextEntryBody,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
    providers: dict = Depends(get_providers),
) -> ContextEntryResponse:
    service = ContextService(db)
    ollama = providers.get("ollama")
    entry = await service.update_entry(
        entry_id=entry_id,
        title=body.title,
        content=body.content,
        category=body.category,
        subcategory=body.subcategory,
        is_active=body.is_active,
        qdrant_client=qdrant_client,
        embed_provider=ollama,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Context entry not found"})
    return ContextEntryResponse(
        id=str(entry.id),
        title=entry.title,
        content=entry.content,
        category=entry.category,
        subcategory=entry.subcategory,
        source_type=entry.source_type,
        source_id=entry.source_id,
        is_active=entry.is_active,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_context_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
) -> None:
    service = ContextService(db)
    success = await service.delete_entry(entry_id=entry_id, qdrant_client=qdrant_client)
    if not success:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Context entry not found"})


@router.post("/extract/text", response_model=ContextEntryResponse, status_code=status.HTTP_201_CREATED)
async def extract_from_text(
    body: ExtractFromTextBody,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
    providers: dict = Depends(get_providers),
) -> ContextEntryResponse:
    """Extract context from free-form text using LLM summarization."""
    service = ContextService(db)
    ollama = providers.get("ollama")

    if ollama:
        try:
            from rain_brain.providers.base import ChatRequest
            req = ChatRequest(
                messages=[
                    {
                        "role": "system",
                        "content": "Anda adalah sekretaris AI. Ringkas percakapan berikut menjadi 1-3 poin kunci dalam Bahasa Indonesia. Format: judul singkat diikuti deskripsi 1-2 kalimat. Output sebagai JSON: {\"title\": \"...\", \"content\": \"...\", \"category\": \"...\"}",
                    },
                    {"role": "user", "content": body.text},
                ],
                model="glm-5.1:cloud",
                temperature=0.1,
                response_format={"type": "json_object"},
                stream=False,
                max_tokens=1024,
            )
            result_text = ""
            async for chunk in ollama.chat(req):
                if chunk.type == "token":
                    result_text += str(chunk.data)
                elif chunk.type == "done":
                    if chunk.data and isinstance(chunk.data, dict):
                        result_text = str(chunk.data.get("content", result_text))

            import json
            try:
                extracted = json.loads(result_text.strip())
                title = extracted.get("title", "Ringkasan Percakapan")
                content = extracted.get("content", result_text[:500])
                category = extracted.get("category", "session")
            except json.JSONDecodeError:
                title = "Ringkasan Percakapan"
                content = result_text[:500] if result_text else body.text[:500]
                category = "session"
        except Exception as e:
            import logging as _log
            _log.getLogger(__name__).warning("extract_from_text LLM failed: %s", e)
            title = "Ringkasan Percakapan"
            content = body.text[:500]
            category = "session"
    else:
        title = "Ringkasan Percakapan"
        content = body.text[:500]
        category = "session"

    entry = await service.create_entry(
        title=title,
        content=content,
        category=category,
        source_type=body.source_type,
        source_id=body.source_id,
        qdrant_client=qdrant_client,
        embed_provider=ollama,
    )
    return ContextEntryResponse(
        id=str(entry.id),
        title=entry.title,
        content=entry.content,
        category=entry.category,
        subcategory=entry.subcategory,
        source_type=entry.source_type,
        source_id=entry.source_id,
        is_active=entry.is_active,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


@router.post("/extract/session/{conversation_id}", response_model=list[ContextEntryResponse], status_code=status.HTTP_201_CREATED)
async def extract_from_session(
    conversation_id: UUID,
    body: ExtractFromSessionBody,
    db: AsyncSession = Depends(get_db),
    qdrant_client=Depends(get_qdrant),
    providers: dict = Depends(get_providers),
) -> list[ContextEntryResponse]:
    service = ContextService(db)
    ollama = providers.get("ollama")
    entries = await service.extract_from_session(
        conversation_id=conversation_id,
        entries=[e.model_dump() for e in body.entries],
        qdrant_client=qdrant_client,
        embed_provider=ollama,
    )
    return [
        ContextEntryResponse(
            id=str(e.id),
            title=e.title,
            content=e.content,
            category=e.category,
            subcategory=e.subcategory,
            source_type=e.source_type,
            source_id=e.source_id,
            is_active=e.is_active,
            created_at=e.created_at.isoformat(),
            updated_at=e.updated_at.isoformat(),
        )
        for e in entries
    ]
