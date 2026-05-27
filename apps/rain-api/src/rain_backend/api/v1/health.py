"""Health check endpoints."""

import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request
from db.schemas.dto_common import HealthResponse
from rain_backend.api.deps import get_db_engine, get_redis, get_providers, get_minio, get_qdrant
from sqlalchemy.ext.asyncio import AsyncEngine
from redis.asyncio import Redis

router = APIRouter(tags=["health"])


async def check_ollama(providers: Dict) -> bool:
    """Check if Ollama is healthy."""
    try:
        ollama_provider = providers.get("ollama")
        if ollama_provider:
            return await asyncio.wait_for(ollama_provider.health(), timeout=2.0)
        return False
    except Exception:
        return False


async def check_postgres(engine: AsyncEngine | None) -> bool:
    """Check if PostgreSQL is healthy."""
    if engine is None:
        return False
    try:
        async with engine.connect():
            return True
    except Exception:
        return False


async def check_redis(redis: Redis | None) -> bool:
    """Check if Redis is healthy."""
    if redis is None:
        return False
    try:
        await asyncio.wait_for(redis.ping(), timeout=2.0)
        return True
    except Exception:
        return False


async def check_minio(minio_client: Any) -> bool:
    """Check if MinIO is healthy."""
    if minio_client is None:
        return False
    try:
        # A simple check like bucket_exists acts as a health check
        from rain_backend.settings import settings
        await asyncio.to_thread(minio_client.bucket_exists, settings.minio_bucket_uploads)
        return True
    except Exception:
        return False


async def check_qdrant(qdrant_client: Any) -> bool:
    """Check if Qdrant is healthy."""
    if qdrant_client is None:
        return False
    try:
        await asyncio.wait_for(qdrant_client.get_collections(), timeout=2.0)
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health_check(
    providers: Dict = Depends(get_providers),
    db_engine: AsyncEngine | None = Depends(get_db_engine),
    redis: Redis | None = Depends(get_redis),
    minio: Any = Depends(get_minio),
    qdrant: Any = Depends(get_qdrant),
) -> HealthResponse:
    """Health check endpoint."""
    results = await asyncio.gather(
        check_ollama(providers),
        check_postgres(db_engine),
        check_redis(redis),
        check_minio(minio),
        check_qdrant(qdrant),
        return_exceptions=True,
    )
    
    # Map results
    def to_bool(val):
        return val if isinstance(val, bool) else False

    ollama_ok = to_bool(results[0])
    postgres_ok = to_bool(results[1])
    redis_ok = to_bool(results[2])
    minio_ok = to_bool(results[3])
    qdrant_ok = to_bool(results[4])
    
    # postgres + redis are required; ollama/minio/qdrant are optional Brain services
    overall_status = "ok" if (postgres_ok and redis_ok) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        ollama=ollama_ok,
        postgres=postgres_ok,
        redis=redis_ok,
        minio=minio_ok,
        qdrant=qdrant_ok,
    )
