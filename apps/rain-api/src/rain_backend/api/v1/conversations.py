"""Conversation CRUD endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from rain_backend.api.deps import get_db
from rain_brain.services.conversation_service import ConversationService
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