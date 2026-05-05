"""Integration tests for chat streaming endpoint."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from rain_backend.main import create_app
from rain_backend.providers.base import ChatChunk


@pytest.fixture
def test_client():
    """Create test client with mocked state."""
    app = create_app()
    # Mock state to avoid connecting to real services
    app.state.providers = {"ollama": MagicMock()}
    app.state.redis = AsyncMock()
    app.state.db_engine = MagicMock()
    app.state.minio = MagicMock()
    app.state.qdrant = AsyncMock()
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_chat_generator():
    """Create mock chat generator."""
    async def generator():
        yield ChatChunk(type="token", data="Hello")
        yield ChatChunk(type="token", data=" world")
        yield ChatChunk(
            type="done",
            data={"tokens_in": 10, "tokens_out": 20},
        )
    return generator()


def test_post_message_stream_success(test_client, mock_chat_generator):
    """Test POST /v1/conversations/{id}/messages streams successfully."""
    conversation_id = uuid4()
    
    # Mock run_chat to use our generator
    with patch("rain_backend.api.v1.messages.run_chat") as mock_run_chat:
        mock_run_chat.return_value = mock_chat_generator
        
        # Make request
        with test_client.stream(
            "POST",
            f"/v1/conversations/{conversation_id}/messages",
            json={"content": "Hello", "model": "kimi-k2.6:cloud"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["cache-control"] == "no-cache"
            
            # Read SSE lines
            lines = []
            for line in response.iter_lines():
                if line:
                    lines.append(line)
    
    # Verify SSE format
    assert len(lines) >= 3
    # Each line should start with "data: "
    for line in lines[:3]:
        assert line.startswith("data: ")
        # Parse JSON
        import json
        data = json.loads(line[6:])  # Remove "data: "
        assert "type" in data
        assert "data" in data


def test_post_message_without_model(test_client, mock_chat_generator):
    """Test POST /v1/conversations/{id}/messages uses default model."""
    conversation_id = uuid4()
    
    with patch("rain_backend.api.v1.messages.run_chat") as mock_run_chat:
        mock_run_chat.return_value = mock_chat_generator
        
        with test_client.stream(
            "POST",
            f"/v1/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
        ) as response:
            assert response.status_code == 200
    
    # Verify default model was used
    call_args = mock_run_chat.call_args
    assert call_args[1]["model"] == "kimi-k2.6:cloud"


def test_post_message_empty_content(test_client):
    """Test POST /v1/conversations/{id}/messages with empty content fails."""
    conversation_id = uuid4()
    
    response = test_client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"content": ""},
    )
    
    assert response.status_code == 422  # Validation error


def test_post_message_content_too_long(test_client):
    """Test POST /v1/conversations/{id}/messages with too long content fails."""
    conversation_id = uuid4()
    long_content = "x" * 10001  # Exceeds max_length=10000
    
    response = test_client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"content": long_content},
    )
    
    assert response.status_code == 422  # Validation error


def test_post_message_stream_error(test_client):
    """Test POST /v1/conversations/{id}/messages when orchestrator yields error."""
    conversation_id = uuid4()
    
    async def error_generator():
        yield ChatChunk(
            type="error",
            data={"code": "conversation_not_found", "message": "Not found"},
        )
    
    with patch("rain_backend.api.v1.messages.run_chat") as mock_run_chat:
        mock_run_chat.return_value = error_generator()
        
        with test_client.stream(
            "POST",
            f"/v1/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
        ) as response:
            assert response.status_code == 200
            
            lines = []
            for line in response.iter_lines():
                if line:
                    lines.append(line)
    
    assert len(lines) == 1
    import json
    data = json.loads(lines[0][6:])
    assert data["type"] == "error"
    assert data["data"]["code"] == "conversation_not_found"


def test_put_message_feedback_success(test_client):
    """Test PUT /v1/messages/{id}/feedback updates feedback successfully."""
    message_id = uuid4()
    mock_message = MagicMock()
    mock_message.id = message_id
    mock_message.feedback = 1
    mock_message.content = "Hello"
    mock_message.role = "assistant"
    mock_message.conversation_id = uuid4()
    mock_message.tokens_in = 10
    mock_message.tokens_out = 20
    mock_message.created_at = "2026-04-23T00:00:00Z"
    mock_message.reasoning_content = None

    with patch("rain_backend.api.v1.messages.MessageService") as mock_service_cls:
        mock_service = AsyncMock()
        mock_service.update_feedback.return_value = mock_message
        mock_service_cls.return_value = mock_service
        
        response = test_client.put(
            f"/v1/messages/{message_id}/feedback",
            json={"feedback": 1},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(message_id)
        assert data["feedback"] == 1


def test_put_message_feedback_not_found(test_client):
    """Test PUT /v1/messages/{id}/feedback returns 404 if message not found."""
    message_id = uuid4()
    
    with patch("rain_backend.api.v1.messages.MessageService") as mock_service_cls:
        mock_service = AsyncMock()
        mock_service.update_feedback.return_value = None
        mock_service_cls.return_value = mock_service
        
        response = test_client.put(
            f"/v1/messages/{message_id}/feedback",
            json={"feedback": -1},
        )
        
        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Message not found"