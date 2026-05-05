---
name: async-fastapi-patterns
description: Use this skill when the Backend Agent is wiring up FastAPI plumbing — app factory, lifespan, dependencies, streaming responses, exception handlers, middleware, or background tasks. Triggers on any new file in api/ or main.py, when adding a new dependency injection point, or debugging async behavior. Enforces the "fully async, never block" discipline that the 4GB hardware budget demands.
---

# Skill: async-fastapi-patterns

## Purpose
Make sure every FastAPI piece is async, non-blocking, properly scoped, and observable. On a 4GB-VRAM machine, blocking the event loop for even a few hundred ms while the LLM is running can cause user-visible lag. Discipline here is non-negotiable.

## When to use
- Creating `main.py` or any new file in `api/`.
- Adding a dependency that holds a connection (DB pool, Redis client, HTTP client).
- Returning a streaming response.
- Handling an exception type for the first time.
- Adding middleware (logging, timing, CORS).

## When NOT to use
- Pure business logic with no I/O → just write the function, no FastAPI ceremony.
- Pydantic schemas → use `pydantic-schema-author` skill.
- Provider implementations → use `provider-adapter-builder` skill.

## App Factory Pattern

`main.py` exposes a single `app` for `uvicorn rain_backend.main:app`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rain_backend.settings import settings
from rain_backend.api.v1 import health, conversations, messages, models
from rain_backend.providers import build_providers
from rain_backend.deps import db_engine, redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.providers = await build_providers(settings)
    app.state.redis = await redis_client(settings.redis_url)
    app.state.db_engine = db_engine(settings.postgres_dsn)
    yield
    # Shutdown
    for p in app.state.providers.values():
        await p.close()
    await app.state.redis.aclose()
    await app.state.db_engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rain Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(conversations.router)
    app.include_router(messages.router)
    app.include_router(models.router)

    return app


app = create_app()
```

**Why factory + lifespan:**
- Connections opened once at startup, reused across requests.
- Tests can call `create_app()` and override dependencies.
- Graceful shutdown closes pools (no orphaned sockets).

## Dependencies

Centralize in `api/deps.py`:

```python
from typing import AsyncIterator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from redis.asyncio import Redis


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = async_sessionmaker(request.app.state.db_engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_providers(request: Request) -> dict:
    return request.app.state.providers
```

**Rules:**
- Dependencies that yield (DB session, Redis pubsub) use `AsyncIterator`.
- Dependencies that return a long-lived object (Redis client, providers dict) just `return`.
- Never instantiate clients in a dependency — pull from `app.state`.

## Streaming Responses (the critical path)

Streaming is how Rain feels fast on a 4GB machine. Every chat response streams.

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from rain_backend.streaming.sse import to_sse
from rain_backend.orchestrator.chat_mode import run_chat

router = APIRouter()

@router.post("/v1/conversations/{conversation_id}/messages")
async def post_message(
    conversation_id: UUID,
    body: PostMessageRequest,
    db: AsyncSession = Depends(get_db),
    providers: dict = Depends(get_providers),
):
    async def event_stream():
        try:
            async for chunk in run_chat(
                conversation_id=conversation_id,
                user_message=body.content,
                model=body.model,
                providers=providers,
                db=db,
            ):
                yield to_sse(chunk)
        except Exception as e:
            # last-resort error chunk so client knows we died
            yield to_sse(ChatChunk(type="error", data={"code": "internal", "message": str(e)}))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx: do not buffer SSE
            "Connection": "keep-alive",
        },
    )
```

`streaming/sse.py`:
```python
import json
from rain_backend.providers.base import ChatChunk

def to_sse(chunk: ChatChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"
```

## Exception Handling

Custom handlers in `main.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Invalid request",
                           "details": exc.errors()}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal", "message": "Internal server error"}},
    )
```

**Never** let an unhandled exception leak the stack trace to the client.

## Logging

Use `logging` (stdlib), structured. In `main.py`:

```python
import logging
import sys

logging.basicConfig(
    level=settings.log_level,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    stream=sys.stdout,
)
```

**What to log:**
- INFO: request started/finished, model selected, cache hit/miss.
- WARNING: provider degraded, fallback engaged, retry triggered.
- ERROR: handled exception, upstream failure.
- DEBUG (off by default): full prompts, full completions.

**Never log at INFO:** API keys, full prompts, full completions, user PII.

## Background Tasks

For fire-and-forget work (e.g., updating embedding cache):

```python
from fastapi import BackgroundTasks

@router.post("/v1/something")
async def handler(body: Body, bg: BackgroundTasks):
    bg.add_task(update_cache_async, body.id)
    return {"ok": True}
```

For longer work (≥ 30s), use a real queue (Phase 3+). For Phase 1, BackgroundTasks is fine.

## Middleware: Request Timing

```python
import time
from starlette.middleware.base import BaseHTTPMiddleware

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
        logger.info(f"{request.method} {request.url.path} {response.status_code} {elapsed_ms:.1f}ms")
        return response

app.add_middleware(TimingMiddleware)
```

## Quality bar
- Zero `def` (sync) handlers. Everything is `async def`.
- Every dependency lives in `api/deps.py`. No inline `Depends(lambda: ...)` mess.
- Streaming responses include the three required headers (`Cache-Control`, `X-Accel-Buffering`, `Connection`).
- Lifespan opens what shutdown closes. Pair them.
- All exceptions caught in handlers. Production never returns a stack trace.

## Anti-patterns
- ❌ Sync `requests` library or `time.sleep` anywhere.
- ❌ Opening a DB session in a route handler instead of via dependency.
- ❌ Returning a dict from a handler — Pydantic only.
- ❌ Catching `Exception` in business logic to silently swallow.
- ❌ Logging the full request body at INFO.
- ❌ CORS `allow_origins=["*"]` in anything but local dev.
