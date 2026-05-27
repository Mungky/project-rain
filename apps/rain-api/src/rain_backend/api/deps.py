"""FastAPI dependencies for the Rain backend."""

from typing import AsyncIterator, Any
from uuid import UUID
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from redis.asyncio import Redis

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


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


async def get_current_user(db: AsyncSession = Depends(get_db)):
    """Return the default single user (auto-created at startup)."""
    from db.schemas import User

    result = await db.execute(
        select(User).where(User.id == DEFAULT_USER_ID)
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    # Fallback: create if missing (should not happen after startup bootstrap)
    user = User(id=DEFAULT_USER_ID, username="rain")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user