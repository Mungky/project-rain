"""FastAPI dependencies for the Rain backend."""

from typing import AsyncIterator, Any
from uuid import UUID
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from redis.asyncio import Redis
import jwt

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


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


async def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Decode JWT and return the authenticated User row."""
    from rain_backend.core.security import decode_access_token
    from db.schemas import User

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise credentials_exc

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exc
    return user


async def require_admin(current_user=Depends(get_current_user)):
    """Raise 403 if the logged-in user is not an admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user