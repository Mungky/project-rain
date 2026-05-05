---
name: pydantic-schema-author
description: Use this skill when the Backend Agent needs to design Pydantic v2 request and response models for a new endpoint, refactor an existing one, or expose a new shape over the API. Triggers on any new endpoint, contract change in CONTRACTS.md, or when OpenAPI generation produces ugly schemas. Enforces consistent naming, validation, and forward-compatibility patterns across the backend.
---

# Skill: pydantic-schema-author

## Purpose
Every byte that crosses the backend boundary (HTTP, WebSocket, queues) is defined by a Pydantic model. This skill produces models that are: (a) consistent across the codebase, (b) generate clean OpenAPI, (c) validate aggressively at the boundary, (d) forward-compatible.

## When to use
- New endpoint being added.
- Contract 2 (HTTP) or Contract 8 (WebSocket) updated.
- Existing handler returns a `dict` (lint failure — fix it).
- OpenAPI client codegen produces `unknown` types (sign of missing/loose schemas).

## When NOT to use
- Internal-only data structures → use dataclasses or plain classes.
- SQLAlchemy models → those live in `db/schemas` and are owned by DB Agent.
- Skill manifest schema → that's JSON Schema, defined separately.

## Naming Conventions

| Kind | Pattern | Example |
|---|---|---|
| Request body | `<Verb><Noun>Request` | `CreateConversationRequest` |
| Response body | `<Noun>Response` or `<Noun>` (entity) | `ConversationResponse`, `Conversation` |
| Path param model | `<Noun>PathParams` | `ConversationPathParams` |
| Query param model | `<Verb><Noun>Query` | `ListConversationsQuery` |
| Embedded sub-object | `<Noun>` (no suffix) | `Message`, `Usage` |
| Streaming envelope | `<Stream>Chunk` | `ChatChunk` |

**Field names:** always `snake_case`. Pydantic handles JSON serialization.

## Procedure

### Step 1: Identify the shape
For the endpoint, list:
- Path params (e.g., `conversation_id`)
- Query params (e.g., `limit`, `cursor`)
- Request body fields
- Response body fields
- Error cases (which lead to which HTTP status)

### Step 2: Write the file
Schemas live in `/backend/src/rain_backend/schemas/<domain>.py`:

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class Message(BaseModel):
    """A single message in a conversation."""
    model_config = ConfigDict(from_attributes=True)  # allow .from_orm

    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    model: str | None = None
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    created_at: datetime


class CreateConversationRequest(BaseModel):
    """Request body for POST /v1/conversations."""
    title: str | None = Field(default=None, max_length=200)


class ConversationResponse(BaseModel):
    """Response for GET /v1/conversations/{id}."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[Message] = Field(default_factory=list)


class ListConversationsQuery(BaseModel):
    """Query params for GET /v1/conversations."""
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None
```

### Step 3: Wire into the handler

```python
from fastapi import APIRouter, Depends, HTTPException
from rain_backend.schemas.conversation import (
    CreateConversationRequest,
    ConversationResponse,
    ListConversationsQuery,
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])

@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    obj = Conversation(title=body.title)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ConversationResponse.model_validate(obj)
```

Note: `response_model=...` is **mandatory** on every route. It's how FastAPI strips internals and how OpenAPI knows the shape.

## Validation Rules (use Field aggressively)

| Concern | Field constraint |
|---|---|
| Strings should not be empty | `min_length=1` |
| Strings should not be huge | `max_length=N` (be generous but bounded) |
| IDs are UUIDs | type `UUID`, never `str` |
| Counts non-negative | `ge=0` |
| Pagination | `ge=1, le=100` |
| Enums | `Literal["a", "b", "c"]` not `str` |
| Optional with default | `field: T | None = None` |
| Required nullable | `field: T | None = Field(...)` |

## Forward Compatibility

**Adding a field:** safe if it has a default. Bump CHANGELOG, no contract break.

**Removing/renaming a field:** breaking. Requires CONTRACTS.md update, BREAKING tag in CHANGELOG, Frontend Agent notification.

**Tightening a constraint** (e.g., max_length 500 → 200): also breaking. Same process.

**Loosening a constraint** (e.g., 200 → 500): non-breaking. Note in CHANGELOG.

## Streaming Envelope (Special Case)

Per Contract 2, every SSE chunk is `ChatChunk`. Defined once, used everywhere:

```python
from typing import Literal, Any
from pydantic import BaseModel

class ChatChunk(BaseModel):
    type: Literal["token", "tool_call", "tool_result", "done", "error"]
    data: Any  # str for token, dict otherwise
```

Don't subclass per chunk type — keep one class. Validate `data` shape at the consumer.

## Error Response Shape (Standardized)

All HTTP errors return:
```python
class ErrorResponse(BaseModel):
    error: dict  # {"code": str, "message": str, "details": dict | None}
```

Use a custom exception handler in `main.py`:
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.detail.get("code", "http_error"),
                           "message": exc.detail.get("message", str(exc.detail))}}
    )
```

## Quality bar
- No `dict` or `Any` in route signatures or response_model (except `ChatChunk.data`).
- Every model has at minimum a one-line docstring.
- `model_config = ConfigDict(from_attributes=True)` on every model that's loaded from SQLAlchemy.
- Field constraints present wherever the underlying data model has constraints.
- OpenAPI rendered at `/docs` shows clean, named types — no anonymous schemas.

## Anti-patterns
- ❌ Returning a `dict` from a handler.
- ❌ Defining the same shape in two places (e.g., once in handler, once in schema).
- ❌ Mixing Pydantic v1 syntax (`Config` class) with v2 (`model_config`).
- ❌ Using `Optional[T]` instead of `T | None` (we're on 3.11+).
- ❌ Validating in the handler what could be validated in the model.
