"""Pytest configuration for Rain backend tests."""

import asyncio
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient
from rain_backend.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for pytest-asyncio."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client for FastAPI app."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client