"""FastAPI dependencies for the Rain backend."""

from typing import AsyncIterator, Any
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from redis.asyncio import Redis


async def get_db_engine(request: Request) -> AsyncEngine:
    """Get the SQLAlchemy async engine from app state."""
    return request.app.state.db_engine


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Get a fresh database session."""
    engine: AsyncEngine = request.app.state.db_engine
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    """Get the Redis client from app state."""
    return request.app.state.redis


def get_providers(request: Request) -> dict[str, Any]:
    """Get providers dict from app state."""
    return request.app.state.providers


def get_minio(request: Request):
    """Get the MinIO client from app state."""
    return request.app.state.minio


def get_qdrant(request: Request):
    """Get the Qdrant async client from app state."""
    return request.app.state.qdrant