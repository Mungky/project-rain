"""Rain Backend FastAPI Application."""

import sys
import os
import pathlib
import logging
import asyncio
import time
from contextlib import asynccontextmanager

# Windows: ProactorEventLoop doesn't support subprocess — switch to Selector
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- PATH INJECTION ---
# Must run before any rain_backend or db imports.
# main.py lives at: apps/rain-api/src/rain_backend/main.py
try:
    _current_file = pathlib.Path(__file__).resolve()
    # src/ = parents[1], rain-api/ = parents[2], apps/ = parents[3], repo root = parents[4]
    _repo_root = _current_file.parents[4]
    _packages = _repo_root / "packages"

    for _p in (_repo_root, _current_file.parents[1], str(_packages)):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
except Exception as _e:
    print(f"Warning: Path injection failed: {_e}")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from redis.asyncio import Redis

# Now we can safely import internal modules
from rain_backend.settings import settings
from rain_backend.api.v1 import (
    health_router,
    conversations_router,
    messages_router,
    documents_router,
    models_router,
    skills_router,
    user_router,
    context_router,
    prompts_router,
    image_gen_router,
    agent_runs_router,
    few_shot_router,
    session_registry_router,
)
from rain_brain.providers import build_providers


# Set up logging
logging.basicConfig(
    level=settings.log_level,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for FastAPI app."""
    logger.info("Starting Rain Backend...")
    
    # Startup
    app.state.providers = await build_providers(settings)
    logger.info(f"Loaded providers: {list(app.state.providers.keys())}")
    
    # Initialize Redis
    try:
        app.state.redis = Redis.from_url(
            settings.redis_url,
            decode_responses=False,
            max_connections=10,
        )
        await app.state.redis.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        app.state.redis = None
    
    # Initialize DB Engine
    try:
        app.state.db_engine = create_async_engine(
            settings.postgres_dsn,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        logger.info("PostgreSQL engine created")
    except Exception as e:
        logger.error(f"PostgreSQL engine creation failed: {e}")
        app.state.db_engine = None

    if app.state.db_engine:
        try:
            async with app.state.db_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.commit()
            logger.info("PostgreSQL connection verified")
        except Exception as e:
            logger.warning(f"PostgreSQL initial connection test failed (will retry on use via pool_pre_ping): {e}")

    # Initialize MinIO
    try:
        from minio import Minio
        minio_endpoint = settings.minio_endpoint or "localhost:9000"
        app.state.minio = Minio(
            endpoint=minio_endpoint,
            access_key=settings.minio_access_key or "rain",
            secret_key=settings.minio_secret_key or "rainminio",
            secure=settings.minio_secure,
        )
        for bucket in (settings.minio_bucket_uploads,):
            if not await asyncio.to_thread(app.state.minio.bucket_exists, bucket):
                await asyncio.to_thread(app.state.minio.make_bucket, bucket)
        logger.info("MinIO initialized and connected (endpoint=%s)", minio_endpoint)
    except Exception as e:
        logger.error("MinIO failed — Neural Archive (file uploads) will be unavailable: %s", e)
        app.state.minio = None

    # Initialize Qdrant
    try:
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import VectorParams, Distance, ScalarQuantization, ScalarType
        
        logger.info(f"Connecting to Qdrant at {settings.qdrant_url}...")
        qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
        
        # Simple health check with retry
        max_retries = 3
        connected = False
        for i in range(max_retries):
            try:
                await qdrant_client.get_collections()
                connected = True
                break
            except Exception as e:
                logger.warning(f"Qdrant connection attempt {i+1} failed: {e}")
                await asyncio.sleep(1)
        
        if connected:
            app.state.qdrant = qdrant_client
            # Ensure collection exists
            collections = await app.state.qdrant.get_collections()
            existing_collections = [c.name for c in collections.collections]
            from qdrant_client.models import ScalarQuantizationConfig
            for collection_name in ("documents", "context_library", "few_shot_library"):
                if collection_name not in existing_collections:
                    logger.info("Creating '%s' collection in Qdrant...", collection_name)
                    await app.state.qdrant.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=settings.qdrant_vector_size, distance=Distance.COSINE),
                        quantization_config=ScalarQuantization(
                            scalar=ScalarQuantizationConfig(
                                type=ScalarType.INT8,
                                always_ram=True,
                            )
                        ),
                    )
            logger.info("Qdrant initialized successfully")
        else:
            logger.error("Failed to connect to Qdrant after retries — Neural Archive (document search) will be unavailable")
            app.state.qdrant = None
    except Exception as e:
        logger.error("Qdrant initialization failure (Neural Archive search unavailable): %s", e, exc_info=True)
        app.state.qdrant = None

    # Sync Skills Registry
    if app.state.db_engine:
        try:
            from rain_brain.services.skill_service import SkillService
            from sqlalchemy.ext.asyncio import async_sessionmaker
            session_factory = async_sessionmaker(app.state.db_engine, expire_on_commit=False)
            async with session_factory() as session:
                skill_service = SkillService(session)
                # Registry is now one level above 'backend' folder
                registry_path = _current_file.parents[4] / "skills_registry"
                if not registry_path.exists():
                    registry_path.mkdir(parents=True, exist_ok=True)
                await skill_service.purge_invalid_skills(registry_path=str(registry_path))
                await skill_service.sync_registry(registry_path=str(registry_path))
            logger.info("Skills registry synchronized")
        except Exception as e:
            logger.error(f"Skills sync failure: {e}")
    
    yield
    
    # Shutdown
    for provider in app.state.providers.values():
        await provider.close()
    if app.state.redis:
        await app.state.redis.aclose()
    if app.state.db_engine:
        await app.state.db_engine.dispose()
    if app.state.qdrant:
        await app.state.qdrant.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(title="Rain Backend", version="0.1.0", lifespan=lifespan)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
        return response
    
    # Exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "http_error",
                    "message": str(exc.detail),
                    "status_code": exc.status_code,
                }
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request",
                    "details": exc.errors(),
                }
            },
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal",
                    "message": "Internal server error",
                }
            },
        )
    
    # Register API routers
    app.include_router(health_router, prefix="/v1", tags=["health"])
    app.include_router(conversations_router, prefix="/v1/conversations", tags=["conversations"])
    app.include_router(messages_router, prefix="/v1", tags=["messages"])
    app.include_router(documents_router, prefix="/v1/documents", tags=["documents"])
    app.include_router(models_router, prefix="/v1/models", tags=["models"])
    app.include_router(skills_router, prefix="/v1/skills", tags=["skills"])
    app.include_router(user_router, prefix="/v1/user", tags=["user"])
    app.include_router(context_router, prefix="/v1/context", tags=["context"])
    app.include_router(prompts_router, prefix="/v1/prompts", tags=["prompts"])
    app.include_router(image_gen_router, prefix="/v1/generate-image", tags=["image-gen"])
    app.include_router(agent_runs_router)
    app.include_router(few_shot_router, prefix="/v1/few-shot", tags=["few-shot"])
    app.include_router(session_registry_router, prefix="/v1/sessions", tags=["sessions"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rain_backend.main:app", host="0.0.0.0", port=8000, reload=True)
