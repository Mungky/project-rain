"""Tests for health check endpoint."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from rain_backend.main import create_app
from rain_backend.providers import build_providers


@pytest.fixture
def mock_providers():
    """Mock providers."""
    ollama_mock = AsyncMock()
    ollama_mock.name = "ollama"
    ollama_mock.health.return_value = True
    ollama_mock.close = AsyncMock()
    
    return {"ollama": ollama_mock}


@pytest.fixture
def mock_db_engine():
    """Mock database engine."""
    engine = MagicMock()
    connection = AsyncMock()
    engine.connect.return_value.__aenter__.return_value = connection
    return engine


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest.mark.asyncio
async def test_health_check_all_healthy(
    mock_providers, mock_db_engine, mock_redis
):
    """Test health endpoint when all services are healthy."""
    # Patch dependencies
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("rain_backend.providers.build_providers", AsyncMock(return_value=mock_providers))
        mp.setattr("rain_backend.api.v1.health.get_providers", lambda: mock_providers)
        mp.setattr("rain_backend.api.v1.health.get_db_engine", lambda: mock_db_engine)
        mp.setattr("rain_backend.api.v1.health.get_redis", lambda: mock_redis)
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["ollama"] is True
        assert data["postgres"] is True
        assert data["redis"] is True


@pytest.mark.asyncio
async def test_health_check_ollama_down(mock_db_engine, mock_redis):
    """Test health endpoint when Ollama is down."""
    mock_ollama = AsyncMock()
    mock_ollama.name = "ollama"
    mock_ollama.health.return_value = False
    mock_providers = {"ollama": mock_ollama}
    
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("rain_backend.providers.build_providers", AsyncMock(return_value=mock_providers))
        mp.setattr("rain_backend.api.v1.health.get_providers", lambda: mock_providers)
        mp.setattr("rain_backend.api.v1.health.get_db_engine", lambda: mock_db_engine)
        mp.setattr("rain_backend.api.v1.health.get_redis", lambda: mock_redis)
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["ollama"] is False
        assert data["postgres"] is True
        assert data["redis"] is True


@pytest.mark.asyncio
async def test_health_check_postgres_down(mock_providers, mock_redis):
    """Test health endpoint when PostgreSQL is down."""
    # Mock db engine that raises an exception
    mock_bad_engine = MagicMock()
    mock_bad_engine.connect.side_effect = Exception("Connection failed")
    
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("rain_backend.providers.build_providers", AsyncMock(return_value=mock_providers))
        mp.setattr("rain_backend.api.v1.health.get_providers", lambda: mock_providers)
        mp.setattr("rain_backend.api.v1.health.get_db_engine", lambda: mock_bad_engine)
        mp.setattr("rain_backend.api.v1.health.get_redis", lambda: mock_redis)
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["ollama"] is True
        assert data["postgres"] is False
        assert data["redis"] is True


@pytest.mark.asyncio
async def test_health_check_redis_down(mock_providers, mock_db_engine):
    """Test health endpoint when Redis is down."""
    mock_bad_redis = AsyncMock()
    mock_bad_redis.ping.side_effect = Exception("Redis connection failed")
    
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("rain_backend.providers.build_providers", AsyncMock(return_value=mock_providers))
        mp.setattr("rain_backend.api.v1.health.get_providers", lambda: mock_providers)
        mp.setattr("rain_backend.api.v1.health.get_db_engine", lambda: mock_db_engine)
        mp.setattr("rain_backend.api.v1.health.get_redis", lambda: mock_bad_redis)
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["ollama"] is True
        assert data["postgres"] is True
        assert data["redis"] is False