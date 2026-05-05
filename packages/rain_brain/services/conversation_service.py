"""Service layer for conversation CRUD operations."""

from uuid import UUID
from datetime import datetime, UTC
from typing import Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas import Conversation as ConversationModel
from db.schemas import Message as MessageModel
from db.schemas import User  # For default user reference
from db.schemas.dto_conversation import (
    Conversation,
    ConversationResponse,
    Message,
)
from rain_brain.config import brain_settings as _settings


# Default user ID from DB seed script
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class ConversationService:
    """Service for conversation CRUD operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_conversation(
        self,
        title: str | None = None,
        persona: str = "drizzle",
    ) -> Conversation:
        """Create a new conversation for the default user."""
        now = datetime.now(UTC)
        conversation = ConversationModel(
            user_id=DEFAULT_USER_ID,
            title=title,
            persona=persona,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        self.db.add(conversation)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(conversation)
        return Conversation.model_validate(conversation)
    
    async def get_conversation(
        self, 
        conversation_id: UUID, 
        include_deleted: bool = False
    ) -> ConversationResponse | None:
        """Get a conversation with its messages."""
        query = select(ConversationModel).where(ConversationModel.id == conversation_id)
        
        if not include_deleted:
            query = query.where(ConversationModel.deleted_at.is_(None))
        
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if conversation is None:
            return None
        
        # Load messages for this conversation
        messages_query = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id
        ).order_by(MessageModel.created_at)
        
        messages_result = await self.db.execute(messages_query)
        messages = messages_result.scalars().all()
        
        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            persona=getattr(conversation, "persona", "drizzle"),
            auto_skills=conversation.auto_skills,
            enabled_skills=conversation.enabled_skills,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            deleted_at=conversation.deleted_at,
            messages=[Message.model_validate(msg) for msg in messages],
        )

    async def list_conversations(
        self, 
        limit: int = 20, 
        cursor: str | None = None
    ) -> tuple[Sequence[Conversation], int]:
        """List conversations for the default user with pagination."""
        # Base query
        query = select(ConversationModel).where(
            ConversationModel.user_id == DEFAULT_USER_ID,
            ConversationModel.deleted_at.is_(None),
        ).order_by(ConversationModel.created_at.desc())
        
        # Cursor-based pagination (simplified for Phase 1)
        if cursor:
            try:
                cursor_time = datetime.fromisoformat(cursor)
                if cursor_time.tzinfo is None:
                    cursor_time = cursor_time.replace(tzinfo=UTC)
                query = query.where(ConversationModel.created_at < cursor_time)
            except ValueError:
                pass
        
        # Get total count
        count_query = select(func.count(ConversationModel.id)).where(
            ConversationModel.user_id == DEFAULT_USER_ID,
            ConversationModel.deleted_at.is_(None),
        )
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar_one()
        
        # Get paginated results
        query = query.limit(limit)
        result = await self.db.execute(query)
        conversations = result.scalars().all()
        
        return [
            Conversation(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                persona=getattr(conv, "persona", "drizzle"),
                auto_skills=conv.auto_skills,
                enabled_skills=conv.enabled_skills,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                deleted_at=conv.deleted_at,
            )
            for conv in conversations
        ], total_count
    
    async def soft_delete_conversation(self, conversation_id: UUID) -> bool:
        """Soft delete a conversation by setting deleted_at timestamp."""
        query = select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if conversation is None:
            return False
        
        conversation.deleted_at = datetime.now(UTC)
        await self.db.commit()
        return True

    async def update_conversation(
        self,
        conversation_id: UUID,
        title: str | None = None,
        persona: str | None = None,
        auto_skills: bool | None = None,
        enabled_skills: list[str] | None = None,
    ) -> ConversationResponse | None:
        """Update conversation fields."""
        query = select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if conversation is None:
            return None
            
        if title is not None:
            conversation.title = title

        if persona is not None:
            conversation.persona = persona

        if auto_skills is not None:
            conversation.auto_skills = auto_skills
            
        if enabled_skills is not None:
            conversation.enabled_skills = enabled_skills
            
        conversation.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        # Load messages so the response is complete
        from db.schemas import Message as MessageModel
        msg_query = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id
        ).order_by(MessageModel.created_at)
        msg_result = await self.db.execute(msg_query)
        messages = msg_result.scalars().all()

        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            persona=getattr(conversation, "persona", "drizzle"),
            auto_skills=conversation.auto_skills,
            enabled_skills=conversation.enabled_skills,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            deleted_at=conversation.deleted_at,
            messages=[Message.model_validate(msg) for msg in messages],
        )
