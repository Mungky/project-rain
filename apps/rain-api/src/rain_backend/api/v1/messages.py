"""Chat streaming endpoints."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from qdrant_client import AsyncQdrantClient
from rain_backend.api.deps import get_db, get_db_engine, get_providers, get_qdrant, get_minio
from db.schemas import UserPreference
from db.schemas.dto_conversation import ConversationPathParams, MessageFeedbackRequest, Message
from db.schemas.dto_chat import PostMessageRequest
from rain_brain.providers.base import ChatChunk
from rain_brain.streaming.sse import to_sse
from rain_brain.orchestrator.chat_mode import run_chat
from rain_brain.services.message_service import MessageService
from rain_backend.api.v1.models import _build_fresh_provider, DEFAULT_USER_ID


logger = logging.getLogger(__name__)
router = APIRouter(tags=["messages"])


async def _providers_with_db_overrides(
    startup_providers: dict, db: AsyncSession
) -> dict:
    """Merge startup providers with user-stored credentials from UserPreference.

    Ensures the chat flow uses the same per-user provider config as ping/list.
    """
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == DEFAULT_USER_ID)
    )
    pref = result.scalar_one_or_none()
    stored = (pref.api_keys or {}) if pref else {}
    merged = dict(startup_providers)
    for name in ("ollama", "anthropic", "openai", "google"):
        cfg = stored.get(name, {})
        fresh = await _build_fresh_provider(name, cfg)
        if fresh is not None:
            merged[name] = fresh
    return merged


@router.put("/messages/{message_id}/feedback", response_model=Message)
async def put_message_feedback(
    message_id: UUID,
    body: MessageFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    providers: dict = Depends(get_providers),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant),
    db_engine: AsyncEngine = Depends(get_db_engine),
) -> Message:
    """Update feedback for a message and feed it into the personalization loop."""
    service = MessageService(db)
    message = await service.update_feedback(message_id, body.feedback)
    if message is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Message not found")

    # Close the learning loop in the background so the click returns instantly:
    # 👍 → save as a high-quality few-shot example; 👎 → learn a style preference.
    if body.feedback in (1, -1):
        try:
            merged = await _providers_with_db_overrides(providers, db)
            from rain_brain.services.feedback_loop import process_feedback_background
            from rain_brain.orchestrator.chat_mode import _fire_and_forget
            _fire_and_forget(
                process_feedback_background(
                    merged, db_engine, qdrant_client, message_id, body.feedback
                )
            )
        except Exception as e:
            logger.warning("feedback loop dispatch failed (non-blocking): %s", e)

    return message


@router.post("/conversations/{conversation_id}/messages")
async def post_message(
    conversation_id: UUID,
    body: PostMessageRequest,
    db: AsyncSession = Depends(get_db),
    providers: dict = Depends(get_providers),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant),
    db_engine: AsyncEngine = Depends(get_db_engine),
    minio_client=Depends(get_minio),
) -> StreamingResponse:
    """Stream chat response for a new message."""

    # Override startup providers with user-stored credentials (Settings UI).
    providers = await _providers_with_db_overrides(providers, db)

    async def event_stream():
        """Generator that streams SSE events."""
        try:
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message=body.content,
                model=body.model,
                providers=providers,
                db=db,
                qdrant_client=qdrant_client,
                attachments=[{"name": a.name, "content": a.content, "mime_type": a.mime_type} for a in body.attachments] if body.attachments else None,
                db_engine=db_engine,
                minio_client=minio_client,
            ):
                yield to_sse(chunk)
        except Exception as e:
            logger.exception(f"Streaming error for conversation {conversation_id}")
            # Last-resort error chunk. Do NOT leak the exception string — it
            # often contains DSNs, API key tails, or other internal detail.
            # The full stack trace is logged above for ops.
            yield to_sse(
                ChatChunk(
                    type="error",
                    data={
                        "code": "internal",
                        "message": "Internal server error. Check server logs for details.",
                    },
                )
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Prevent nginx from buffering SSE
            "Connection": "keep-alive",
        },
    )