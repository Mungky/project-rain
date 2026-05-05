# INSTRUCTIONS.md — Backend Agent

## Required Reading Before You Code
1. `/PRD.md` — full
2. `/CONTRACTS.md` — full (you implement most of it)
3. `/backend/SYSTEM_PROMPT.md`
4. This file
5. The latest WO in `/backend/INBOX/`

## Your Folder Layout (build it as you go)

```
/backend
├── INBOX/                          # WOs from Parent land here
├── README.md                       # how to run, test, debug
├── pyproject.toml                  # uv or poetry; pinned deps
├── .python-version                 # 3.11
├── alembic.ini                     # points at db/alembic (DB Agent owns migrations)
├── src/
│   └── rain_backend/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory
│       ├── settings.py             # Pydantic Settings, reads env
│       ├── api/
│       │   ├── __init__.py
│       │   ├── v1/
│       │   │   ├── __init__.py
│       │   │   ├── health.py
│       │   │   ├── conversations.py
│       │   │   ├── messages.py
│       │   │   └── models.py       # GET /v1/models
│       │   └── deps.py             # FastAPI dependencies
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py             # Protocol from Contract 7
│       │   ├── ollama.py           # Phase 1
│       │   ├── anthropic.py        # Phase 2
│       │   ├── openai.py           # Phase 2
│       │   ├── google.py           # Phase 2
│       │   └── browser.py          # Phase 4-Optional
│       ├── orchestrator/
│       │   ├── chat_mode.py        # Phase 1: simple linear chat
│       │   ├── work_mode.py        # Phase 3: multi-agent planner
│       │   └── critic.py           # Phase 3
│       ├── memory/
│       │   ├── short_term.py       # Redis
│       │   ├── episodic.py         # Qdrant
│       │   ├── semantic.py         # Postgres
│       │   └── working.py          # in-process scratchpad
│       ├── skills/
│       │   ├── executor.py         # Docker sandbox runner
│       │   ├── registry.py         # query installed skills
│       │   └── manifest.py         # validate skill.yaml
│       ├── streaming/
│       │   └── sse.py              # SSE envelope helpers
│       └── schemas/                # Pydantic models (request/response)
│           ├── chat.py
│           ├── conversation.py
│           └── skill.py
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_providers/
    │   ├── test_orchestrator/
    │   └── test_memory/
    └── integration/
        └── test_chat_e2e.py
```

## Skills You Have Loaded
See `/backend/skills/`. Currently:
- `provider-adapter-builder` — implement a new LLM provider conforming to Contract 7
- `pydantic-schema-author` — design request/response models for endpoints
- `async-fastapi-patterns` — idiomatic streaming, dependencies, error handling
- `prompt-engineering-for-tiny-models` — get good output from 3B models (the core "Match Opus" skill)

## Standard Operating Procedures

### SOP-1: Implementing a New Endpoint
1. Read the WO. Identify which Contract section governs the endpoint.
2. Write the Pydantic request and response models in `schemas/` first.
3. Write the unit test for the route handler with a mocked provider.
4. Implement the handler. Make the test pass.
5. Verify OpenAPI: `curl localhost:8000/openapi.json | jq '.paths' | grep <your-path>` shows the endpoint with correct schema.
6. Add an integration test if the endpoint is user-facing.
7. CHANGELOG entry. Mark WO complete.

### SOP-2: Adding a Provider
Use the `provider-adapter-builder` skill. In short:
1. Subclass `Provider` Protocol from `providers/base.py`.
2. Implement all four methods (`list_models`, `chat`, `embed`, `health`).
3. `chat` is an async generator yielding `ChatChunk`.
4. Errors caught and yielded as `ChatChunk(type="error", ...)`, never raised.
5. Tests: at minimum, mock the upstream HTTP and verify chunk sequence for happy path + one error path.

### SOP-3: Streaming a Response (SSE)
Always use the helpers in `streaming/sse.py`. Pseudocode:
```python
from fastapi.responses import StreamingResponse
from rain_backend.streaming.sse import to_sse

async def stream():
    async for chunk in orchestrator.run(request):
        yield to_sse(chunk)  # serializes to "data: {...}\n\n"

return StreamingResponse(stream(), media_type="text/event-stream")
```
Never yield raw strings. Always go through `to_sse` so the envelope shape (Contract 2) is enforced.

### SOP-4: Caching with Redis
Use the helper in `memory/short_term.py` (you'll write it). Pattern:
```python
key = f"rain:cache:llm:{sha256(prompt)}"
cached = await redis.get(key)
if cached:
    return json.loads(cached)
result = await expensive_call()
await redis.setex(key, ttl_seconds, json.dumps(result))
return result
```
Every Redis key follows Contract 5 conventions. Every key has a TTL. Period.

### SOP-5: Working with the Database
Never write raw SQL. Never write a migration. Both are DB Agent's territory.
```python
from db.schemas import Conversation, Message
from sqlalchemy.ext.asyncio import AsyncSession

async def list_conversations(session: AsyncSession, user_id: UUID):
    stmt = select(Conversation).where(Conversation.user_id == user_id)
    return (await session.scalars(stmt)).all()
```

### SOP-6: Phase 1 Walking Skeleton — Build Order
This is your Phase 1 execution sequence. Do NOT reorder.
1. `settings.py` — read env vars per Contract 1.
2. `main.py` — minimal FastAPI app + lifespan that opens/closes Redis & Postgres pools.
3. `providers/base.py` — Protocol & DTOs (Contract 7).
4. `providers/ollama.py` — implement against local Ollama.
5. `api/v1/health.py` — first endpoint, proves wiring works.
6. `schemas/chat.py` + `schemas/conversation.py` — DTOs.
7. `api/v1/conversations.py` — CRUD on conversations.
8. `streaming/sse.py` — SSE helpers.
9. `orchestrator/chat_mode.py` — linear: load history → call provider → stream → persist.
10. `api/v1/messages.py` — POST endpoint that uses chat_mode.
11. Integration test for end-to-end chat.

## Quality Bar
- All code passes `ruff check` and `ruff format`.
- All public functions have type hints.
- Tests use `pytest-asyncio`, never `asyncio.run` in tests.
- No `print` statements. Use `logging` with structured fields.
- No `time.sleep` — use `asyncio.sleep`.

## Anti-Patterns to Avoid
- ❌ `requests` library (sync). Use `httpx`.
- ❌ Bare `except:` clauses.
- ❌ Returning dicts from endpoints — return Pydantic models.
- ❌ Storing prompts or completions at INFO log level (PII risk).
- ❌ Reading env vars outside `settings.py`.
- ❌ Importing from `frontend/` or writing to its files.

## When Stuck
1. Re-read the relevant WO and Contract.
2. Search the codebase for prior patterns.
3. If still stuck, write a comment to Parent in the WO file explaining the ambiguity. Wait for clarification. Do not guess on contract surface.
