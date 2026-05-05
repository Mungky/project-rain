# CONTRACTS.md — Inter-Agent Interfaces

**Status:** Authoritative. Changing anything here requires Parent Agent approval + CHANGELOG entry.

This file is the single source of truth for how the four folders talk to each other. If your code violates a contract here, your code is wrong, not the contract.

---

## Contract 1: Environment Variables (Owned by Parent, Consumed by All)

All env vars live in `/.env.example` at root. Never hardcode. Never duplicate the list.

```
# --- LLM Providers ---
OLLAMA_BASE_URL=http://localhost:11434
ANTHROPIC_API_KEY=                # Phase 2+
OPENAI_API_KEY=                   # Phase 2+
GOOGLE_API_KEY=                   # Phase 2+

# --- Datastores ---
POSTGRES_DSN=postgresql+asyncpg://rain:rain@localhost:5432/rain
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000     # Phase 2+
MINIO_ACCESS_KEY=                 # Phase 2+
MINIO_SECRET_KEY=                 # Phase 2+

# --- Backend ---
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_LOG_LEVEL=INFO

# --- Frontend ---
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

---

## Contract 2: Backend ↔ Frontend HTTP

**Source of truth:** FastAPI's auto-generated OpenAPI at `GET /openapi.json`.

Frontend MUST regenerate types on every backend version bump:
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts
```

### Phase 1 endpoints
- `POST /v1/conversations` — create conversation, returns `{id, created_at}`
- `GET /v1/conversations` — list user's conversations
- `GET /v1/conversations/{id}` — full conversation with messages
- `POST /v1/conversations/{id}/messages` — append message; SSE stream of response
- `DELETE /v1/conversations/{id}` — soft delete
- `GET /v1/health` — `{status: "ok", ollama: bool, postgres: bool, redis: bool}`
- `GET /v1/models` — list available models from current providers

### Streaming envelope (SSE)
Every server-sent event is `data: <json>\n\n` where json matches:
```json
{"type": "token", "data": "Hello"}
{"type": "tool_call", "data": {"name": "search", "args": {...}}}
{"type": "tool_result", "data": {"name": "search", "result": "..."}}
{"type": "done", "data": {"message_id": "uuid", "usage": {...}}}
{"type": "error", "data": {"code": "...", "message": "..."}}
```

Frontend must handle every `type` and ignore unknown types gracefully (forward-compat).

---

## Contract 3: Backend ↔ DB (Postgres)

DB Agent publishes a Python package at `/db/schemas/` containing SQLAlchemy 2.x async models. Backend imports from there:

```python
from db.schemas import Conversation, Message, User
```

**Backend never writes raw migrations.** All schema changes go through DB Agent's Alembic.

### Core tables (Phase 1)
- `conversations` — id, user_id, title, created_at, updated_at, deleted_at
- `messages` — id, conversation_id, role, content, model, tokens_in, tokens_out, created_at
- `users` — id, name, created_at (single-user but keep table for forward compat)

### Phase 2 tables
- `documents` — id, user_id, filename, mime, minio_key, qdrant_collection, status
- `skills` — id, name, version, manifest_json, docker_image, installed_at, enabled
- `skill_executions` — id, skill_id, conversation_id, input, output, duration_ms, error

### Phase 3 tables
- `agent_runs` — id, conversation_id, plan_json, status, started_at, finished_at
- `agent_tasks` — id, run_id, parent_task_id, role, input, output, status

---

## Contract 4: Backend ↔ DB (Qdrant)

Collections defined in `/db/qdrant_collections.yaml`. Backend reads this file at startup to know what's available.

**Phase 2 collections:**
```yaml
collections:
  - name: documents
    vector_size: 768          # nomic-embed-text dim
    distance: Cosine
  - name: episodic_memory     # Phase 3
    vector_size: 768
    distance: Cosine
```

Naming: snake_case. Never embed user_id in collection name (use payload filter).

Payload schema for `documents`:
```json
{
  "user_id": "uuid",
  "document_id": "uuid",
  "chunk_index": 0,
  "text": "raw chunk text",
  "source": "filename or url"
}
```

---

## Contract 5: Backend ↔ DB (Redis)

Key conventions in `/db/REDIS_KEYS.md`. Summary:

```
rain:session:{user_id}                      # current session blob, TTL 24h
rain:cache:embed:{sha256-of-text}           # embedding cache, TTL 7d
rain:cache:llm:{sha256-of-prompt-hash}      # LLM response cache, TTL 1h
rain:agent:run:{run_id}:state               # work-mode runtime state, TTL 1h
rain:agent:run:{run_id}:queue               # task queue (LIST), TTL 1h
rain:lock:{resource}                        # distributed locks, TTL 30s
```

Use namespacing strictly. Never store outside `rain:*` namespace.

---

## Contract 6: Skill Manifest Schema (Phase 2+)

JSON Schema lives at `/backend/schemas/skill_manifest.schema.json`. Every skill repo's `manifest.yaml` must validate against it.

```yaml
name: web-search-duckduckgo
version: 0.1.0
description: Search the web via DuckDuckGo. Returns top 10 results.
runtime: python3.11
entry: handler.py:handle
inputs:
  query:
    type: string
    description: Search query
    required: true
  max_results:
    type: integer
    default: 10
outputs:
  results:
    type: array
    items: {type: object}
permissions:
  network: true
  filesystem: false
  duration_seconds_max: 30
```

---

## Contract 7: Provider Adapter Interface (Backend internal, but contract-grade)

All LLM providers implement:

```python
from typing import AsyncIterator
from pydantic import BaseModel

class ChatRequest(BaseModel):
    messages: list[dict]
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = True
    response_format: dict | None = None  # for JSON mode
    tools: list[dict] | None = None

class ChatChunk(BaseModel):
    type: str  # "token" | "tool_call" | "done" | "error"
    data: dict | str

class Provider(Protocol):
    name: str
    async def list_models(self) -> list[str]: ...
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def health(self) -> bool: ...
```

Phase 1 implementations: `OllamaProvider` only.
Phase 2 adds: `AnthropicProvider`, `OpenAIProvider`, `GoogleProvider`.
Phase 4-Optional: `BrowserProvider` (clearly marked risky).

---

## Contract 8: WebSocket (Phase 3 — Work Mode)

URL: `ws://host:8000/ws/agent-runs/{run_id}`

Server pushes events as JSON:
```json
{"event": "run_started", "data": {...}}
{"event": "task_created", "data": {"task_id": "...", "role": "planner"}}
{"event": "task_status", "data": {"task_id": "...", "status": "running"}}
{"event": "task_output", "data": {"task_id": "...", "output": "..."}}
{"event": "task_completed", "data": {"task_id": "...", "output": "..."}}
{"event": "run_completed", "data": {"final_output": "..."}}
```

Frontend renders these as nodes in the agent graph.

---

## Conflict Resolution

If two agents disagree about a contract, the disagreement goes to Parent Agent. Parent Agent updates this file and notifies all affected agents. **Do not silently work around contracts.**
