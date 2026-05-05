"""Tests for conversation CRUD endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from rain_backend.main import create_app


@pytest.fixture
def test_client():
    """Create test client with mocked dependencies."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_conversation_service():
    """Mock conversation service."""
    service = MagicMock()
    service.create_conversation = AsyncMock()
    service.get_conversation = AsyncMock()
    service.list_conversations = AsyncMock()
    service.soft_delete_conversation = AsyncMock()
    return service


def test_create_conversation(test_client, mock_conversation_service):
    """Test POST /v1/conversations."""
    conversation_id = uuid4()
    created_at = datetime.now(UTC)
    
    mock_conversation = MagicMock()
    mock_conversation.id = conversation_id
    mock_conversation.created_at = created_at
    
    mock_conversation_service.create_conversation.return_value = mock_conversation
    
    # Patch service in the endpoint
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.post("/v1/conversations", json={"title": "Test Conversation"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(conversation_id)
    assert "created_at" in data


def test_create_conversation_no_title(test_client, mock_conversation_service):
    """Test POST /v1/conversations without title."""
    conversation_id = uuid4()
    created_at = datetime.now(UTC)
    
    mock_conversation = MagicMock()
    mock_conversation.id = conversation_id
    mock_conversation.created_at = created_at
    
    mock_conversation_service.create_conversation.return_value = mock_conversation
    
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.post("/v1/conversations", json={})
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(conversation_id)


def test_list_conversations(test_client, mock_conversation_service):
    """Test GET /v1/conversations."""
    mock_conversations = [
        MagicMock(
            id=uuid4(),
            user_id=uuid4(),
            title="Conversation 1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        ),
        MagicMock(
            id=uuid4(),
            user_id=uuid4(),
            title=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        ),
    ]
    
    mock_conversation_service.list_conversations.return_value = (mock_conversations, 10)
    
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.get("/v1/conversations")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 10
    assert len(data["conversations"]) == 2
    assert data["conversations"][0]["title"] == "Conversation 1"
    assert data["conversations"][1]["title"] is None


def test_list_conversations_with_pagination(test_client, mock_conversation_service):
    """Test GET /v1/conversations with pagination parameters."""
    mock_conversations = [
        MagicMock(
            id=uuid4(),
            user_id=uuid4(),
            title="Paginated",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        ),
    ]
    
    mock_conversation_service.list_conversations.return_value = (mock_conversations, 15)
    
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.get("/v1/conversations?limit=5&cursor=2025-01-01T00:00:00")
    
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert "total_count" in data
    assert data["total_count"] == 15


def test_get_conversation_exists(test_client, mock_conversation_service):
    """Test GET /v1/conversations/{id}."""
    conversation_id = uuid4()
    
    mock_conversation_response = MagicMock()
    mock_conversation_response.id = conversation_id
    mock_conversation_response.user_id = uuid4()
    mock_conversation_response.title = "Test Conversation"
    mock_conversation_response.created_at = datetime.now(UTC)
    mock_conversation_response.updated_at = datetime.now(UTC)
    mock_conversation_response.deleted_at = None
    mock_conversation_response.messages = []
    
    mock_conversation_service.get_conversation.return_value = mock_conversation_response
    
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.get(f"/v1/conversations/{conversation_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(conversation_id)
    assert data["title"] == "Test Conversation"


def test_get_conversation_not_found(test_client, mock_conversation_service):
    """Test GET /v1/conversations/{id} when conversation doesn't exist."""
    conversation_id = uuid4()
    
    mock_conversation_service.get_conversation.return_value = None
    
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.get(f"/v1/conversations/{conversation_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "conversation_not_found"


def test_delete_conversation_success(test_client, mock_conversation_service):
    """Test DELETE /v1/conversations/{id}."""
    conversation_id = uuid4()
    
    mock_conversation_service.soft_delete_conversation.return_value = True
    
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.delete(f"/v1/conversations/{conversation_id}")
    
    assert response.status_code == 204


def test_delete_conversation_not_found(test_client, mock_conversation_service):
    """Test DELETE /v1/conversations/{id} when conversation doesn't exist."""
    conversation_id = uuid4()
    
    mock_conversation_service.soft_delete_conversation.return_value = False
    
    with patch(
        "rain_backend.api.v1.conversations.ConversationService",
        return_value=mock_conversation_service,
    ):
        response = test_client.delete(f"/v1/conversations/{conversation_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "conversation_not_found"