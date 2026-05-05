"""Tests for conversation service."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas import Conversation as ConversationModel
from db.schemas import Message as MessageModel
from rain_backend.services.conversation_service import ConversationService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def conversation_service(mock_db):
    """Conversation service with mocked DB."""
    return ConversationService(mock_db)


@pytest.mark.asyncio
async def test_create_conversation(conversation_service, mock_db):
    """Test creating a conversation."""
    mock_conversation = MagicMock()
    mock_conversation.id = uuid4()
    mock_conversation.user_id = conversation_service.DEFAULT_USER_ID
    mock_conversation.title = "Test Conversation"
    mock_conversation.model = "kimi-k2.6:cloud"
    mock_conversation.created_at = datetime.now(UTC)
    mock_conversation.updated_at = datetime.now(UTC)
    mock_conversation.deleted_at = None
    
    # Mock the add/commit/refresh pattern
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Service should create ConversationModel instance
    with patch.object(ConversationModel, "__init__", return_value=None):
        # Mock the created conversation object
        conversation_instance = ConversationModel()
        conversation_instance.id = mock_conversation.id
        conversation_instance.user_id = mock_conversation.user_id
        conversation_instance.title = mock_conversation.title
        conversation_instance.created_at = mock_conversation.created_at
        conversation_instance.updated_at = mock_conversation.updated_at
        conversation_instance.deleted_at = mock_conversation.deleted_at
        
        # Mock validate
        with patch("rain_backend.services.conversation_service.Conversation.model_validate") as mock_validate:
            mock_validate.return_value = mock_conversation
            
            result = await conversation_service.create_conversation("Test Conversation")
    
    assert result.id == mock_conversation.id
    assert result.title == "Test Conversation"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_conversation_no_title(conversation_service, mock_db):
    """Test creating a conversation without title."""
    mock_conversation = MagicMock()
    mock_conversation.id = uuid4()
    mock_conversation.user_id = conversation_service.DEFAULT_USER_ID
    mock_conversation.title = None
    mock_conversation.created_at = datetime.now(UTC)
    mock_conversation.updated_at = datetime.now(UTC)
    mock_conversation.deleted_at = None
    
    with patch.object(ConversationModel, "__init__", return_value=None):
        with patch("rain_backend.services.conversation_service.Conversation.model_validate") as mock_validate:
            mock_validate.return_value = mock_conversation
            
            result = await conversation_service.create_conversation(None)
    
    assert result.id == mock_conversation.id
    assert result.title is None


@pytest.mark.asyncio
async def test_get_conversation_exists(conversation_service, mock_db):
    """Test getting an existing conversation."""
    conversation_id = uuid4()
    mock_conversation = MagicMock()
    mock_conversation.id = conversation_id
    mock_conversation.user_id = conversation_service.DEFAULT_USER_ID
    mock_conversation.title = "Test"
    mock_conversation.model = "kimi-k2.6:cloud"
    mock_conversation.created_at = datetime.now(UTC)
    mock_conversation.updated_at = datetime.now(UTC)
    mock_conversation.deleted_at = None
    
    mock_messages = [
        MagicMock(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content="Hello",
            tokens_in=5,
            tokens_out=0,
            created_at=datetime.now(UTC),
        ),
        MagicMock(
            id=uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content="Hi!",
            tokens_in=0,
            tokens_out=10,
            created_at=datetime.now(UTC),
        ),
    ]
    
    # Mock select query for conversation
    mock_result_conversation = AsyncMock()
    mock_result_conversation.scalar_one_or_none.return_value = mock_conversation
    mock_db.execute.return_value = mock_result_conversation
    
    # Mock messages query
    mock_result_messages = AsyncMock()
    mock_result_messages.scalars.return_value.all.return_value = mock_messages
    mock_db.execute.side_effect = [mock_result_conversation, mock_result_messages]
    
    # Mock Message.model_validate
    with patch("rain_backend.services.conversation_service.Message.model_validate") as mock_msg_validate:
        mock_msg_validate.side_effect = lambda msg: msg
        
        result = await conversation_service.get_conversation(conversation_id)
    
    assert result.id == conversation_id
    assert len(result.messages) == 2
    assert result.messages[0].content == "Hello"
    assert result.messages[1].content == "Hi!"


@pytest.mark.asyncio
async def test_get_conversation_not_found(conversation_service, mock_db):
    """Test getting a non-existent conversation."""
    conversation_id = uuid4()
    
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await conversation_service.get_conversation(conversation_id)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_conversation_deleted(conversation_service, mock_db):
    """Test getting a deleted conversation with include_deleted=False."""
    conversation_id = uuid4()
    
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await conversation_service.get_conversation(conversation_id, include_deleted=False)
    
    assert result is None


@pytest.mark.asyncio
async def test_list_conversations(conversation_service, mock_db):
    """Test listing conversations."""
    mock_conversations = [
        MagicMock(
            id=uuid4(),
            user_id=conversation_service.DEFAULT_USER_ID,
            title="Conversation 1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        ),
        MagicMock(
            id=uuid4(),
            user_id=conversation_service.DEFAULT_USER_ID,
            title=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        ),
    ]
    
    # Mock count query
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 2
    
    # Mock list query
    mock_list_result = AsyncMock()
    mock_list_result.scalars.return_value.all.return_value = mock_conversations
    
    mock_db.execute.side_effect = [mock_count_result, mock_list_result]
    
    # Mock Conversation.model_validate
    with patch("rain_backend.services.conversation_service.Conversation.model_validate") as mock_validate:
        mock_validate.side_effect = lambda conv: conv
        
        conversations, total_count = await conversation_service.list_conversations()
    
    assert total_count == 2
    assert len(conversations) == 2
    assert conversations[0].title == "Conversation 1"
    assert conversations[1].title is None


@pytest.mark.asyncio
async def test_list_conversations_with_limit_and_cursor(conversation_service, mock_db):
    """Test listing conversations with pagination."""
    mock_conversations = [
        MagicMock(
            id=uuid4(),
            user_id=conversation_service.DEFAULT_USER_ID,
            title="Conversation 1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        ),
    ]
    
    # Mock count query
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 5
    # Mock list query
    mock_list_result = AsyncMock()
    mock_list_result.scalars.return_value.all.return_value = mock_conversations
    
    mock_db.execute.side_effect = [mock_count_result, mock_list_result]
    
    # Mock Conversation.model_validate
    with patch("rain_backend.services.conversation_service.Conversation.model_validate") as mock_validate:
        mock_validate.side_effect = lambda conv: conv
        
        conversations, total_count = await conversation_service.list_conversations(limit=1, cursor="2025-01-01T00:00:00")
    
    assert total_count == 5  # Example total count
    assert len(conversations) == 1
    assert conversations[0].title == "Conversation 1"


@pytest.mark.asyncio
async def test_soft_delete_conversation_success(conversation_service, mock_db):
    """Test soft deleting a conversation."""
    conversation_id = uuid4()
    mock_conversation = MagicMock()
    mock_conversation.id = conversation_id
    mock_conversation.user_id = conversation_service.DEFAULT_USER_ID
    mock_conversation.deleted_at = None
    
    # Mock select query
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_conversation
    mock_db.execute.return_value = mock_result
    
    result = await conversation_service.soft_delete_conversation(conversation_id)
    
    assert result is True
    assert mock_conversation.deleted_at is not None
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_soft_delete_conversation_not_found(conversation_service, mock_db):
    """Test soft deleting a non-existent conversation."""
    conversation_id = uuid4()
    
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await conversation_service.soft_delete_conversation(conversation_id)
    
    assert result is False
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_soft_delete_conversation_already_deleted(conversation_service, mock_db):
    """Test soft deleting an already deleted conversation."""
    conversation_id = uuid4()
    
    # Mock conversation that's already deleted (deleted_at not None)
    mock_conversation = MagicMock()
    mock_conversation.id = conversation_id
    mock_conversation.user_id = conversation_service.DEFAULT_USER_ID
    mock_conversation.deleted_at = datetime.now(UTC)  # Already deleted
    
    # Mock select query but with .where(deleted_at.is_(None)) which will exclude deleted records
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await conversation_service.soft_delete_conversation(conversation_id)
    
    assert result is False
    mock_db.commit.assert_not_called()