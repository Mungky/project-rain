"""Tests for OllamaProvider."""

import json
import pytest
import pytest_httpx
from unittest.mock import AsyncMock, patch
from rain_backend.providers.ollama import OllamaProvider
from rain_backend.providers.base import ChatRequest


@pytest.mark.asyncio
async def test_list_models_success(httpx_mock: pytest_httpx.HTTPXMock):
    """Test listing models successfully."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/tags",
        json={
            "models": [
                {"name": "kimi-k2.6:cloud"},
                {"name": "llama3.2:3b-instruct-q4_K_M"},
            ]
        }
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    models = await provider.list_models()
    
    assert models == ["kimi-k2.6:cloud", "llama3.2:3b-instruct-q4_K_M"]


@pytest.mark.asyncio
async def test_list_models_empty_response(httpx_mock: pytest_httpx.HTTPXMock):
    """Test listing models with empty response."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/tags",
        json={"models": []}
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    models = await provider.list_models()
    
    assert models == []


@pytest.mark.asyncio
async def test_list_models_http_error(httpx_mock: pytest_httpx.HTTPXMock):
    """Test listing models when HTTP request fails."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/tags",
        status_code=500
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    models = await provider.list_models()
    
    assert models == []


@pytest.mark.asyncio
async def test_chat_streams_tokens(httpx_mock: pytest_httpx.HTTPXMock):
    """Test chat streams tokens successfully."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/chat",
        json={
            "model": "kimi-k2.6:cloud",
            "message": {"content": "Hello"},
            "done": False
        }
    )
    
    # Mock streaming response
    mock_response = httpx_mock.add_response(
        url="http://localhost:11434/api/chat",
        stream=[
            b'{"model":"qwen2.5:3b","message":{"content":"Hello"},"done":false}\n',
            b'{"model":"qwen2.5:3b","message":{"content":" world"},"done":false}\n',
            b'{"model":"qwen2.5:3b","done":true,"prompt_eval_count":10,"eval_count":20}\n',
        ]
    )
    mock_response.stream = True
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    request = ChatRequest(
        messages=[{"role": "user", "content": "Hello"}],
        model="kimi-k2.6:cloud",
        stream=True,
    )
    
    chunks = []
    async for chunk in provider.chat(request):
        chunks.append(chunk)
    
    assert len(chunks) == 3
    assert chunks[0].type == "token"
    assert chunks[0].data == "Hello"
    assert chunks[1].type == "token"
    assert chunks[1].data == " world"
    assert chunks[2].type == "done"
    assert chunks[2].data["tokens_in"] == 10
    assert chunks[2].data["tokens_out"] == 20


@pytest.mark.asyncio
async def test_chat_yields_error_on_http_failure(httpx_mock: pytest_httpx.HTTPXMock):
    """Test chat yields error when HTTP request fails."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/chat",
        status_code=500
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    request = ChatRequest(
        messages=[{"role": "user", "content": "Hello"}],
        model="kimi-k2.6:cloud",
        stream=True,
    )
    
    chunks = []
    async for chunk in provider.chat(request):
        chunks.append(chunk)
    
    assert len(chunks) == 1
    assert chunks[0].type == "error"
    assert chunks[0].data["code"] == "upstream_http"
    assert "500" in str(chunks[0].data["message"])


@pytest.mark.asyncio
async def test_health_true(httpx_mock: pytest_httpx.HTTPXMock):
    """Test health returns True when Ollama responds successfully."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/tags",
        status_code=200
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    result = await provider.health()
    
    assert result is True


@pytest.mark.asyncio
async def test_health_false_on_http_error(httpx_mock: pytest_httpx.HTTPXMock):
    """Test health returns False when HTTP request fails."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/tags",
        status_code=500
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    result = await provider.health()
    
    assert result is False


@pytest.mark.asyncio
async def test_health_false_on_timeout():
    """Test health returns False when request times out."""
    # Create provider with very short timeout
    provider = OllamaProvider(base_url="http://127.0.0.1:1", timeout=0.01)  # Invalid address
    result = await provider.health()
    
    assert result is False


@pytest.mark.asyncio
async def test_embed_success(httpx_mock: pytest_httpx.HTTPXMock):
    """Test embedding generation."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/embeddings",
        json={"embedding": [0.1, 0.2, 0.3]}
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    embeddings = await provider.embed(["test text"])
    
    assert embeddings == [[0.1, 0.2, 0.3]]


@pytest.mark.asyncio
async def test_embed_empty_list():
    """Test embedding with empty input."""
    provider = OllamaProvider(base_url="http://localhost:11434")
    embeddings = await provider.embed([])
    
    assert embeddings == []


@pytest.mark.asyncio
async def test_embed_http_error(httpx_mock: pytest_httpx.HTTPXMock):
    """Test embedding returns empty on HTTP error."""
    httpx_mock.add_response(
        url="http://localhost:11434/api/embeddings",
        status_code=500
    )
    
    provider = OllamaProvider(base_url="http://localhost:11434")
    embeddings = await provider.embed(["test text"])
    
    assert embeddings == [[]]  # Returns empty embedding list on error


@pytest.mark.asyncio
async def test_close():
    """Test closing the provider."""
    provider = OllamaProvider(base_url="http://localhost:11434")
    # Should not raise
    await provider.close()