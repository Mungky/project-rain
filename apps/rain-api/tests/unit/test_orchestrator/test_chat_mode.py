"""Tests for chat_mode orchestrator."""

import pytest
from uuid import uuid4
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from rain_backend.orchestrator.chat_mode import run_chat
from rain_backend.providers.base import ChatChunk, ChatRequest
from db.schemas.message import MessageRole


@pytest.fixture
def mock_db():
    """Mock database session with proper execute() return values."""
    mock = AsyncMock()
    # Mock execute() to return a result with scalar_one_or_none and scalars methods
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    mock.execute = AsyncMock(return_value=mock_result)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock


@pytest.fixture
def mock_providers():
    """Mock providers dict with Ollama provider."""
    ollama_mock = MagicMock()
    ollama_mock.embed = AsyncMock(return_value=[[0.1] * 768])
    ollama_mock.chat = MagicMock(return_value=mock_chat_generator())
    return {"ollama": ollama_mock}


@pytest.fixture
def mock_conversation():
    """Mock conversation with messages."""
    conversation_id = uuid4()

    user_msg = MagicMock()
    user_msg.role = MessageRole.user
    user_msg.content = "Hello"
    user_msg.role_value = "user"

    assistant_msg = MagicMock()
    assistant_msg.role = MessageRole.assistant
    assistant_msg.content = "Hi there!"
    assistant_msg.role_value = "assistant"

    conversation_mock = MagicMock()
    conversation_mock.id = conversation_id
    conversation_mock.messages = [user_msg, assistant_msg]
    return conversation_mock


async def mock_chat_generator():
    """Mock async generator for provider.chat."""
    # Yield a token
    yield ChatChunk(type="token", data="Hello")
    yield ChatChunk(type="token", data=" world")

    # Yield done with usage stats
    yield ChatChunk(
        type="done",
        data={
            "tokens_in": 10,
            "tokens_out": 20,
        },
    )


@pytest.mark.asyncio
async def test_run_chat_success(
    mock_db, mock_providers, mock_conversation
):
    """Test successful chat flow."""
    conversation_id = uuid4()

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.user,
                content="Test message",
            )
            mock_message_service_cls.return_value = mock_message_service

            # Mock provider
            mock_providers["ollama"].chat = MagicMock(return_value=mock_chat_generator())

            # Run the chat
            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test message",
                model="kimi-k2.6:cloud",
                providers=mock_providers,
                db=mock_db,
            ):
                chunks.append(chunk)

    # Verify chunks
    assert len(chunks) == 3
    assert chunks[0].type == "token"
    assert chunks[0].data == "Hello"
    assert chunks[1].type == "token"
    assert chunks[1].data == " world"
    assert chunks[2].type == "done"
    assert chunks[2].data["tokens_in"] == 10

    # Verify message was created for assistant response
    mock_message_service.create_message.assert_called()
    # Should be called twice: once for user, once for assistant
    assert mock_message_service.create_message.call_count == 2


@pytest.mark.asyncio
async def test_run_chat_conversation_not_found(
    mock_db, mock_providers
):
    """Test chat when conversation doesn't exist."""
    conversation_id = uuid4()
    
    # Mock conversation service to return None
    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService"
    ) as mock_conversation_service_cls:
        mock_conversation_service = AsyncMock()
        mock_conversation_service.get_conversation.return_value = None
        mock_conversation_service_cls.return_value = mock_conversation_service
    
    chunks = []
    async for chunk in run_chat(
        conversation_id=conversation_id,
        user_message="Test message",
        model="qwen2.5:3b",
        providers=mock_providers,
        db=mock_db,
    ):
        chunks.append(chunk)
    
    assert len(chunks) == 1
    assert chunks[0].type == "error"
    assert chunks[0].data["code"] == "conversation_not_found"


@pytest.mark.asyncio
async def test_run_chat_provider_unavailable(
    mock_db, mock_conversation
):
    """Test chat when Ollama provider is unavailable."""
    conversation_id = uuid4()
    providers = {}  # No providers

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    # Mock message service to avoid db.add issues
    mock_message_service = AsyncMock()
    mock_message_service.create_message.return_value = MagicMock(
        id=uuid4(),
        role=MessageRole.user,
        content="Test message",
    )

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService",
            return_value=mock_message_service,
        ):
            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test message",
                model="qwen2.5:3b",
                providers=providers,
                db=mock_db,
            ):
                chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].type == "error"
    assert chunks[0].data["code"] == "provider_unavailable"


@pytest.mark.asyncio
async def test_run_chat_provider_error(
    mock_db, mock_providers, mock_conversation
):
    """Test chat when provider returns an error."""
    conversation_id = uuid4()

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.user,
                content="Test message",
            )
            mock_message_service_cls.return_value = mock_message_service

            # Mock provider to yield error chunk
            async def error_generator(*args, **kwargs):
                yield ChatChunk(
                    type="error",
                    data={"code": "upstream_error", "message": "Provider error"},
                )

            mock_providers["ollama"].chat = MagicMock(return_value=error_generator())

            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test message",
                model="qwen2.5:3b",
                providers=mock_providers,
                db=mock_db,
            ):
                chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].type == "error"
    assert chunks[0].data["code"] == "upstream_error"


@pytest.mark.asyncio
async def test_run_chat_early_error(
    mock_db, mock_providers, mock_conversation
):
    """Test chat when user message creation fails."""
    conversation_id = uuid4()

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service to raise exception
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.side_effect = Exception("DB error")
            mock_message_service_cls.return_value = mock_message_service

            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test message",
                model="qwen2.5:3b",
                providers=mock_providers,
                db=mock_db,
            ):
                chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].type == "error"
    assert chunks[0].data["code"] == "database_error"


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client with query_points method."""
    qdrant_mock = AsyncMock()
    qdrant_mock.query_points = AsyncMock()
    return qdrant_mock


@pytest.mark.asyncio
async def test_run_chat_with_rag_context(
    mock_db, mock_providers, mock_conversation, mock_qdrant
):
    """Test chat with RAG context from Qdrant."""
    conversation_id = uuid4()

    # Mock Qdrant to return relevant chunks
    mock_qdrant.query_points.return_value = MagicMock(
        points=[
            MagicMock(
                payload={
                    "text": "Rain is a local AI assistant.",
                    "source": "readme.md",
                }
            ),
            MagicMock(
                payload={
                    "text": "Rain runs on Ollama.",
                    "source": "setup.md",
                }
            ),
        ]
    )

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    # Create a proper mock conversation service
    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.user,
                content="Test message",
            )
            mock_message_service_cls.return_value = mock_message_service

            # Mock provider chat
            mock_providers["ollama"].chat = MagicMock(return_value=mock_chat_generator())

            # Run the chat with Qdrant
            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="What is Rain?",
                model="kimi-k2.6:cloud",
                providers=mock_providers,
                db=mock_db,
                qdrant_client=mock_qdrant,
            ):
                chunks.append(chunk)

    # Verify Qdrant was queried
    mock_qdrant.query_points.assert_called_once()

    # Verify done chunk contains citations
    done_chunk = chunks[-1]
    assert done_chunk.type == "done"
    assert "citations" in done_chunk.data
    assert set(done_chunk.data["citations"]) == {"readme.md", "setup.md"}


@pytest.mark.asyncio
async def test_run_chat_qdrant_unavailable(
    mock_db, mock_providers, mock_conversation
):
    """Test chat falls back to normal when Qdrant is None."""
    conversation_id = uuid4()

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.user,
                content="Test message",
            )
            mock_message_service_cls.return_value = mock_message_service

            # Mock provider chat
            mock_providers["ollama"].chat = MagicMock(return_value=mock_chat_generator())

            # Run the chat without Qdrant
            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test message",
                model="kimi-k2.6:cloud",
                providers=mock_providers,
                db=mock_db,
                qdrant_client=None,
            ):
                chunks.append(chunk)

    # Verify normal chat flow works
    assert len(chunks) == 3
    assert chunks[-1].type == "done"
    # No citations when Qdrant is unavailable
    assert "citations" not in chunks[-1].data or not chunks[-1].data.get("citations")


@pytest.mark.asyncio
async def test_run_chat_qdrant_empty_results(
    mock_db, mock_providers, mock_conversation, mock_qdrant
):
    """Test chat falls back when Qdrant returns no results."""
    conversation_id = uuid4()

    # Mock Qdrant to return empty results
    mock_qdrant.query_points.return_value = MagicMock(points=[])

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.user,
                content="Test message",
            )
            mock_message_service_cls.return_value = mock_message_service

            # Mock provider chat
            mock_providers["ollama"].chat = MagicMock(return_value=mock_chat_generator())

            # Run the chat
            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test message",
                model="kimi-k2.6:cloud",
                providers=mock_providers,
                db=mock_db,
                qdrant_client=mock_qdrant,
            ):
                chunks.append(chunk)

    # Verify normal chat flow works (fallback)
    assert len(chunks) == 3
    assert chunks[-1].type == "done"


@pytest.mark.asyncio
async def test_run_chat_qdrant_search_fails(
    mock_db, mock_providers, mock_conversation, mock_qdrant
):
    """Test chat falls back when Qdrant search raises exception."""
    conversation_id = uuid4()

    # Mock Qdrant to raise exception
    mock_qdrant.query_points.side_effect = Exception("Qdrant error")

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.user,
                content="Test message",
            )
            mock_message_service_cls.return_value = mock_message_service

            # Mock provider chat
            mock_providers["ollama"].chat = MagicMock(return_value=mock_chat_generator())

            # Run the chat
            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test message",
                model="kimi-k2.6:cloud",
                providers=mock_providers,
                db=mock_db,
                qdrant_client=mock_qdrant,
            ):
                chunks.append(chunk)

    # Verify normal chat flow works (fallback)
    assert len(chunks) == 3
    assert chunks[-1].type == "done"


@pytest.mark.asyncio
async def test_run_chat_citations_in_done_chunk(
    mock_db, mock_providers, mock_conversation, mock_qdrant
):
    """Test that citations appear in done chunk data."""
    conversation_id = uuid4()

    # Mock Qdrant to return chunks with citations
    mock_qdrant.query_points.return_value = MagicMock(
        points=[
            MagicMock(
                payload={
                    "text": "Rain uses Ollama for inference.",
                    "source": "architecture.md",
                }
            ),
        ]
    )

    # Mock conversation service - get_conversation is async
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        # Mock message service
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.user,
                content="Test message",
            )
            mock_message_service_cls.return_value = mock_message_service

            # Mock provider chat
            mock_providers["ollama"].chat = MagicMock(return_value=mock_chat_generator())

            # Run the chat
            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="What does Rain use?",
                model="kimi-k2.6:cloud",
                providers=mock_providers,
                db=mock_db,
                qdrant_client=mock_qdrant,
            ):
                chunks.append(chunk)

    # Verify citations in done chunk
    done_chunk = chunks[-1]
    assert done_chunk.type == "done"
    assert "citations" in done_chunk.data
    assert done_chunk.data["citations"] == ["architecture.md"]


@pytest.mark.asyncio
async def test_run_chat_reasoning_extraction(
    mock_db, mock_providers, mock_conversation
):
    """Test that <think> tags are extracted as reasoning content."""
    conversation_id = uuid4()

    # Mock conversation service
    async def mock_get_conversation(cid):
        return mock_conversation

    mock_conversation_service = MagicMock()
    mock_conversation_service.get_conversation = mock_get_conversation

    async def reasoning_generator():
        """Yield tokens with <think> tags."""
        yield ChatChunk(type="token", data="Thought: <think>")
        yield ChatChunk(type="token", data="Thinking process")
        yield ChatChunk(type="token", data=" here.</think> Final answer.")
        yield ChatChunk(
            type="done",
            data={"tokens_in": 5, "tokens_out": 10},
        )

    with patch(
        "rain_backend.orchestrator.chat_mode.ConversationService",
        return_value=mock_conversation_service,
    ):
        with patch(
            "rain_backend.orchestrator.chat_mode.MessageService"
        ) as mock_message_service_cls:
            mock_message_service = AsyncMock()
            mock_message_service.create_message.return_value = MagicMock(
                id=uuid4(),
                role=MessageRole.assistant,
                content="Thought:  Final answer.",
                reasoning_content="Thinking process here.",
            )
            mock_message_service_cls.return_value = mock_message_service

            mock_providers["ollama"].chat = MagicMock(return_value=reasoning_generator())

            chunks = []
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message="Test thinking",
                model="deepseek-r1:7b",
                providers=mock_providers,
                db=mock_db,
            ) :
                chunks.append(chunk)

    # Verify chunks
    # Expected chunks:
    # 1. token: "Thought: "
    # 2. reasoning: "Thinking process"
    # 3. reasoning: " here."
    # 4. token: " Final answer."
    # 5. done
    
    # Filter for types
    token_chunks = [c for c in chunks if c.type == "token"]
    reasoning_chunks = [c for c in chunks if c.type == "reasoning"]
    
    assert "".join([c.data for c in token_chunks]) == "Thought:  Final answer."
    assert "".join([c.data for c in reasoning_chunks]) == "Thinking process here."
    
    # Verify DB call
    mock_message_service.create_message.assert_called()
    # Find assistant call
    assistant_call = None
    for call in mock_message_service.create_message.call_args_list:
        if call.kwargs.get("role") == MessageRole.assistant:
            assistant_call = call
            break
    
    assert assistant_call is not None
    assert assistant_call.kwargs["content"] == "Thought:  Final answer."
    assert assistant_call.kwargs["reasoning_content"] == "Thinking process here."