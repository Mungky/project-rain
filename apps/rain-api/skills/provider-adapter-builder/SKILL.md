---
name: provider-adapter-builder
description: Use this skill when the Backend Agent needs to implement a new LLM provider (Ollama, Anthropic, OpenAI, Google, browser-based, or any future addition) that conforms to Contract 7. Triggers when adding a provider in providers/, when a WO mentions "wire up <provider>", or when refactoring an existing provider. Walks through the full implementation including the four required methods, error handling, streaming chunk shapes, and required tests.
---

# Skill: provider-adapter-builder

## Purpose
Implement a new LLM provider that satisfies Contract 7 (Provider Adapter Interface). The adapter pattern is what lets the rest of Rain not care whether tokens come from a 3B model running locally, a frontier hosted API, or a browser-automated session.

## When to use
- WO says "implement <provider>" or "add <provider> support".
- Refactoring an existing provider for a contract change.
- Adding a mock provider for tests.

## When NOT to use
- Modifying the `Provider` Protocol itself → that's a Contract 7 change, requires Parent + CONTRACTS.md update first.
- Adding orchestration logic → that goes in `orchestrator/`, not in the provider.
- Building skill executors → that's `skills/executor.py`, not a provider.

## Required interface (from Contract 7)

```python
from typing import AsyncIterator, Protocol
from pydantic import BaseModel

class ChatRequest(BaseModel):
    messages: list[dict]
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = True
    response_format: dict | None = None
    tools: list[dict] | None = None

class ChatChunk(BaseModel):
    type: str   # "token" | "tool_call" | "tool_result" | "done" | "error"
    data: dict | str

class Provider(Protocol):
    name: str
    async def list_models(self) -> list[str]: ...
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def health(self) -> bool: ...
```

## Procedure

### Step 1: Scaffold
Create `/backend/src/rain_backend/providers/<provider_name>.py`:

```python
from typing import AsyncIterator
import httpx
from rain_backend.providers.base import Provider, ChatRequest, ChatChunk
from rain_backend.settings import settings

class <Provider>Provider:
    name = "<provider_name>"

    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 60.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )

    async def list_models(self) -> list[str]:
        ...

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def health(self) -> bool:
        try:
            r = await self._client.get("<health-endpoint>")
            return r.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
```

### Step 2: Implement `chat` correctly

This is where most adapters fail. Rules:

1. **`chat` is an async generator.** Use `async def chat(...) -> AsyncIterator[ChatChunk]:` then `yield`. Never return a list.

2. **The first byte should appear ASAP.** Open the streaming HTTP call before any other work.

3. **Wrap the upstream stream's parsing in try/except.** Yield `ChatChunk(type="error", data={"code": ..., "message": ...})` on failure, then return. Never raise out of the generator.

4. **End every successful stream with `ChatChunk(type="done", data={...})`** including usage stats if available.

5. **Tool/function calls (Phase 2+):** if upstream returns a tool call, yield `ChatChunk(type="tool_call", data={"name": ..., "arguments": ...})`. The orchestrator handles execution.

Example shape (Ollama-flavored):

```python
async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
    payload = {
        "model": req.model,
        "messages": req.messages,
        "stream": True,
        "options": {"temperature": req.temperature, "num_predict": req.max_tokens},
    }
    if req.response_format:
        payload["format"] = req.response_format

    try:
        async with self._client.stream("POST", "/api/chat", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("done"):
                    yield ChatChunk(type="done", data={
                        "model": obj.get("model"),
                        "tokens_in": obj.get("prompt_eval_count", 0),
                        "tokens_out": obj.get("eval_count", 0),
                    })
                    return
                content = obj.get("message", {}).get("content", "")
                if content:
                    yield ChatChunk(type="token", data=content)
    except httpx.HTTPError as e:
        yield ChatChunk(type="error", data={"code": "upstream_http", "message": str(e)})
    except Exception as e:
        yield ChatChunk(type="error", data={"code": "internal", "message": str(e)})
```

### Step 3: Implement `embed`

For providers that don't have an embed endpoint (e.g., Anthropic), raise `NotImplementedError` and document. Rain will route embeds to Ollama by default.

### Step 4: Register the provider

Add to `providers/__init__.py`:
```python
from rain_backend.providers.ollama import OllamaProvider
from rain_backend.providers.<provider_name> import <Provider>Provider

PROVIDERS: dict[str, type[Provider]] = {
    "ollama": OllamaProvider,
    "<provider_name>": <Provider>Provider,
}
```

### Step 5: Tests (mandatory)

Create `/backend/tests/unit/test_providers/test_<provider_name>.py`:

```python
import pytest
from pytest_httpx import HTTPXMock
from rain_backend.providers.<provider_name> import <Provider>Provider
from rain_backend.providers.base import ChatRequest

@pytest.mark.asyncio
async def test_chat_streams_tokens(httpx_mock: HTTPXMock):
    # Mock the upstream stream
    httpx_mock.add_response(
        url="...",
        stream=...  # multi-line streaming response
    )
    p = <Provider>Provider(base_url="...", api_key="test")
    chunks = [c async for c in p.chat(ChatRequest(messages=[...], model="..."))]
    assert chunks[0].type == "token"
    assert chunks[-1].type == "done"

@pytest.mark.asyncio
async def test_chat_yields_error_on_http_failure(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=500)
    p = <Provider>Provider(base_url="...", api_key="test")
    chunks = [c async for c in p.chat(ChatRequest(messages=[...], model="..."))]
    assert any(c.type == "error" for c in chunks)

@pytest.mark.asyncio
async def test_health_returns_false_on_unreachable():
    p = <Provider>Provider(base_url="http://127.0.0.1:1", api_key="x")
    assert await p.health() is False
```

Minimum: happy chat path, error chat path, health true, health false, list_models. Coverage on the new file ≥ 80%.

## Provider-specific notes

### Ollama
- Base URL: `http://localhost:11434`
- No auth.
- `embed` endpoint: `POST /api/embeddings` with `{"model": "nomic-embed-text", "prompt": "..."}`. Loop for batches.
- For 4GB VRAM: keep `keep_alive: "5m"` short to free memory; don't pin huge models.

### Anthropic
- Base URL: `https://api.anthropic.com`
- Auth: header `x-api-key: <key>` and `anthropic-version: 2023-06-01`.
- Streaming via SSE: parse `event: ` and `data: ` lines.
- No embedding endpoint — raise `NotImplementedError`.

### OpenAI
- Standard. Use SSE parsing. Handle `[DONE]` sentinel.
- Embedding model: `text-embedding-3-small` (1536 dim — note: doesn't match Qdrant collection of 768 unless you reconfigure or downsample).

### Google (Gemini)
- API surface different — read latest docs, parse Server-Sent JSON.

### Browser (Phase 4-Optional, RISKY)
- Wraps Playwright. Holds a persistent context with user's logged-in session.
- DO NOT IMPLEMENT until user has explicitly accepted the warnings in PRD §8.
- Even then: gate behind `settings.enable_browser_provider` flag, default off.
- Treat as best-effort, no SLA, expect breakage on every provider UI update.

## Quality bar
- Generator never raises. Errors become chunks.
- No blocking I/O (`requests`, `time.sleep`, sync DB calls).
- Settings come from `settings.py`, never `os.getenv` directly.
- Health check has bounded timeout (≤ 2s), never hangs.

## Anti-patterns
- ❌ Returning a list from `chat` instead of yielding.
- ❌ Letting an upstream HTTP error propagate out of the generator.
- ❌ Hardcoding model names inside the provider.
- ❌ Forgetting to send a final `done` chunk.
- ❌ Closing the HTTP client per-request instead of reusing.
