"""Service layer for message operations."""

from uuid import UUID
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas import Message as MessageModel
from db.schemas.message import MessageRole
from db.schemas.dto_conversation import Message as MessageSchema


class MessageService:
    """Service for message CRUD operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        reasoning_content: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        attachments: list[dict] | None = None,
        model: str | None = None,
        tool_events: list[dict] | None = None,
        react_steps: list[dict] | None = None,
    ) -> MessageSchema:
        """Create a new message."""
        message = MessageModel(
            conversation_id=conversation_id,
            role=role,
            content=content,
            reasoning_content=reasoning_content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            attachments=attachments or None,
            model=model,
            tool_events=tool_events or None,
            react_steps=react_steps or None,
            created_at=datetime.now(UTC),
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return MessageSchema.model_validate(message)
    
    async def update_feedback(
        self,
        message_id: UUID,
        feedback: int | None,
    ) -> MessageSchema | None:
        """Update feedback for a message."""
        query = select(MessageModel).where(MessageModel.id == message_id)
        result = await self.db.execute(query)
        message = result.scalar_one_or_none()
        
        if message is None:
            return None
            
        message.feedback = feedback
        await self.db.commit()
        await self.db.refresh(message)
        return MessageSchema.model_validate(message)
    
    async def get_conversation_messages(self, conversation_id: UUID) -> list[MessageSchema]:
        """Get all messages for a conversation."""
        query = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id
        ).order_by(MessageModel.created_at)
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        return [MessageSchema.model_validate(msg) for msg in messages]