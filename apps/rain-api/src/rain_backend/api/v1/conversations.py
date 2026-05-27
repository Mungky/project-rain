"""Conversation CRUD endpoints."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from rain_backend.api.deps import get_db, get_providers
from rain_brain.services.conversation_service import ConversationService
from rain_brain.services.message_service import MessageService
from db.schemas.dto_conversation import (
    CreateConversationRequest,
    UpdateConversationRequest,
    ConversationCreatedResponse,
    ConversationResponse,
    ConversationListResponse,
    Conversation,
    ListConversationsQuery,
    ConversationPathParams,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["conversations"])


@router.post(
    "",
    response_model=ConversationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    body: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationCreatedResponse:
    """Create a new conversation."""
    service = ConversationService(db)
    conversation = await service.create_conversation(
        title=body.title,
        persona=body.persona,
    )
    
    return ConversationCreatedResponse(
        id=conversation.id,
        created_at=conversation.created_at,
    )


@router.get(
    "",
    response_model=ConversationListResponse,
)
async def list_conversations(
    query: ListConversationsQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """List conversations for the user."""
    service = ConversationService(db)
    conversations, total_count = await service.list_conversations(
        limit=query.limit,
        cursor=query.cursor,
    )
    
    next_cursor = None
    if conversations and len(conversations) >= query.limit:
        last_conversation = conversations[-1]
        next_cursor = last_conversation.created_at.isoformat()
    
    return ConversationListResponse(
        conversations=conversations,
        total_count=total_count,
        next_cursor=next_cursor,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation(
    path: ConversationPathParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Get a conversation with its messages."""
    service = ConversationService(db)
    conversation = await service.get_conversation(path.conversation_id)
    
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "conversation_not_found",
                "message": f"Conversation {path.conversation_id} not found",
            },
        )
    
    return conversation


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
async def update_conversation(
    body: UpdateConversationRequest,
    path: ConversationPathParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Update conversation settings."""
    service = ConversationService(db)
    conversation = await service.update_conversation(
        conversation_id=path.conversation_id,
        title=body.title,
        persona=body.persona,
        auto_skills=body.auto_skills,
        enabled_skills=body.enabled_skills,
    )
    
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "conversation_not_found",
                "message": f"Conversation {path.conversation_id} not found or already deleted",
            },
        )
    
    return conversation


@router.post("/{conversation_id}/auto-title", response_model=ConversationResponse)
async def auto_title_conversation(
    path: ConversationPathParams = Depends(),
    db: AsyncSession = Depends(get_db),
    providers: dict = Depends(get_providers),
) -> ConversationResponse:
    """Generate a short title from the conversation history and persist it.

    Frontend calls this after the second assistant message lands. Idempotent
    in spirit: caller decides when to invoke (we always overwrite the title).
    """
    conv_svc = ConversationService(db)
    conversation = await conv_svc.get_conversation(path.conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation_not_found",
                    "message": f"Conversation {path.conversation_id} not found"},
        )

    msg_svc = MessageService(db)
    msgs = await msg_svc.get_conversation_messages(path.conversation_id)
    if not msgs:
        return conversation
    msgs = msgs[:6]

    # Build a tiny transcript for the model to summarise.
    snippets = []
    for m in msgs:
        role = "User" if m.role == "user" else "Assistant"
        body = (m.content or "").strip()
        if not body:
            continue
        snippets.append(f"{role}: {body[:300]}")
    transcript = "\n".join(snippets)

    prompt = (
        "Generate a concise 3–6 word title (no quotes, no trailing punctuation) "
        "summarising this chat. Title must be in the same language as the user. "
        "Respond with the title only, nothing else.\n\n"
        f"{transcript}"
    )

    provider = providers.get(conversation.model.split(":", 1)[0] if conversation.model else "ollama") \
        or providers.get("ollama")
    if provider is None:
        logger.warning("auto_title: no provider available")
        return conversation

    try:
        from rain_brain.providers.base import ChatRequest
        req = ChatRequest(
            messages=[{"role": "user", "content": prompt}],
            model=conversation.model or "kimi-k2.6",
            max_tokens=20,
            stream=False,
        )
        title = ""
        async for chunk in provider.chat(req):
            if chunk.type == "token":
                title += str(chunk.data or "")
            elif chunk.type == "done":
                break
        title = title.strip().strip('"').strip("'").strip().splitlines()[0] if title.strip() else ""
        if title and title != conversation.title:
            updated = await conv_svc.update_conversation(
                conversation_id=path.conversation_id,
                title=title[:80],
            )
            return updated or conversation
    except Exception as e:
        logger.warning("auto_title generation failed: %s", e)

    return conversation


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    path: ConversationPathParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a conversation."""
    service = ConversationService(db)
    deleted = await service.soft_delete_conversation(path.conversation_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "conversation_not_found",
                "message": f"Conversation {path.conversation_id} not found or already deleted",
            },
        )