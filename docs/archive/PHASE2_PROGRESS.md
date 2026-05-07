# Phase 2 Progress — Memory & Skills
**Status:** ✅ Completed  
**Period:** 2026-04-22 → 2026-04-25  
**Closed by:** Parent Agent (2026-04-23), extended with agent capability upgrades

---

## What Phase 2 Set Out to Do (per PRD)

| Item | Status |
|---|---|
| Qdrant integration: document upload → chunk → embed → store | ✅ Done |
| RAG retrieval injected into chat context | ✅ Done |
| MinIO for raw file storage | ✅ Done |
| `skills.sh install` CLI for skill ecosystem | ✅ Done |
| Skill executor runtime | ✅ Done |
| Hosted API providers (Anthropic, OpenAI, Google) | ✅ Done |
| Frontend: file upload UI | ✅ Done |
| Frontend: skill management panel | ✅ Done |

---

## What Actually Shipped (Full Breakdown)

### Infrastructure

**Vector Store (Qdrant)**
- `documents` collection (768-dim, Cosine, int8 quantization) auto-created on startup
- `context_library` collection for agent-extracted knowledge
- RAG retrieval injects top-4 chunks from both collections into chat context
- Semantic deduplication on save (`score_threshold=0.82`)

**Object Storage (MinIO)**
- `rain-uploads` bucket for raw document files
- `rain-skill-artifacts` bucket for skill build artifacts
- Async download via `asyncio.to_thread(response.read)`

**SearXNG**
- Self-hosted search aggregator in `docker-compose.yml` (port 8080)
- Aggregates Google, Bing, DuckDuckGo, Wikipedia
- JSON API enabled for skill consumption

---

### Backend

**Document Pipeline** (`/v1/documents`)
- `POST /v1/documents` — multipart upload → MinIO storage → text chunking (~512 tokens) → Ollama embedding → Qdrant upsert
- `GET /v1/documents` — paginated listing with status polling
- `DELETE /v1/documents/{id}` — full cleanup across Postgres + MinIO + Qdrant
- `GET /v1/documents/{id}/download` — stream original file from MinIO

**Skill Ecosystem**
- `skills.sh` CLI for install/list/remove
- Skill Executor runtime (`skill_executor.py`)
- Skills registered in Postgres with manifest JSON
- 3 built-in skills shipped:
  - `web-search-searxng` — live web search via SearXNG (replaced DuckDuckGo)
  - `web-reader` — fetch and clean full webpage text (stdlib-only)
  - `python-executor` — isolated subprocess with 30s timeout, returns stdout/stderr
- `POST /v1/skills/sync` — on-demand registry sync without restart

**Hosted Provider Adapters**
- `AnthropicProvider` — Claude 3.5 Sonnet, Claude 3 Haiku, Claude Opus 4.7
- `OpenAIProvider` — GPT-4o, GPT-4o Mini, GPT-4 Turbo
- `GoogleProvider` — Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 2.0 Flash
- Dynamic provider instantiation from DB-stored API keys (no env var required)
- Model Registry (`providers/model_registry.py`) — single source of truth for all model IDs

**Memory System**
- `MEMORY_TOOL` — built-in tool for silent episodic memory writes (`update_user_memory`)
- `PreferenceService` — upserts key-value pairs into `user_preferences.user_context`
- `CONTEXT_TOOL` — built-in tool for agent to save research findings to context library
- `ContextService` — CRUD for `context_library` collection (Qdrant + Postgres)
- Context library entries injected into every system prompt (proactive awareness)
- Background context extraction after every response (`gemma4:31b-cloud`, fire-and-forget)

**Chat Orchestrator Upgrades**
- Adaptive temperature (`detect_task_type()` → temperature mapping)
- Context window management (keeps last 24 messages, notes omitted count)
- Session-specific skill filtering (`auto_skills` + `enabled_skills` per conversation)
- Custom system prompt + user context injection from preferences
- `neural_context` SSE chunk — streams RAG chunks to frontend in real-time

**Observability**
- Langfuse integration (`langfuse>=2.0.0`) with graceful no-op fallback
- `RainTracer` — `_Noop` pattern, zero impact when keys not set
- Spans: `chat` (top-level) → `rag` → `react_iter_N` → `tool:{name}`
- Enable with: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`

**ReAct Loop**
- Replaced recursive `process_stream` with explicit `for _iter in range(8)` loop
- Tools stay available across all iterations (true multi-step reasoning)
- Max 8 tool iterations per request
- Tool results properly appended to message history between iterations

**API Endpoints Added**
- `GET /v1/models` — unified model list across all providers
- `GET /v1/user/preferences` + `PATCH /v1/user/preferences`
- `PUT /v1/messages/{id}/feedback` — thumbs up/down
- `GET /v1/skills` — list installed skills
- `POST /v1/skills/sync`
- `PATCH /v1/conversations/{id}` — update model, title, skill config

**Bug Fixes**
- Model defaulting to kimi on every conversation fixed
- Tool args NameError fixed (was silently failing all skill execution)
- `ChatRequest.messages` type widened to `dict[str, Any]` (tool_call messages rejected by Pydantic)
- `enabled_skills` filter now supports both UUID and name matching
- Model bleeding between conversations (locked existing sessions to their stored model)
- Attachment binary validation (`.docx`, `.pdf` rejected before `file.text()`)

---

### Database

**New Models / Migrations**
- `Document` — tracks upload status, minio_key, qdrant vectors
- `Skill` + `SkillExecution` — skill registry and execution logs
- `UserPreference` — custom system prompt, user context, API keys (JSONB)
- `Conversation.auto_skills` (Boolean) + `enabled_skills` (JSONB)
- `Message.feedback` (integer) + `reasoning_content` (text)
- `ContextEntry` — context library entries with category/subcategory

**Schema**
- All datetime columns migrated to `TIMESTAMPTZ`
- `UTCDatetime` annotated type ensuring timezone-aware output

---

### Frontend

**Chat UI/UX Polish**
- `ThinkingBlock` — collapsible reasoning display, auto-expands during streaming, live elapsed timer, bouncing dots indicator
- Tool call pills — per-tool spinner (calling) → green lightning (done)
- Feedback buttons (thumbs up/down) on assistant messages
- Copy button with "Copied" flash feedback
- Edit button on user messages
- Auto-scroll during streaming + "jump to bottom" button
- `no-scrollbar` on conversation list

**Panels**
- **Left panel**: `flex-1 min-h-0` fix — Workshop + Settings always pinned at bottom
- **Middle panel**: Model selector moved to composer; ContextExtractorBadge replaces it in header (Brain icon, idle/extracting/synced states); conversation title removed from header
- **Right panel**:
  - Usage tab: token counts + IDR cost + animated per-model progress bars
  - Skills tab: read-only list (removed Auto Mode toggle and per-skill toggles)
  - Neural Context tab: search bar, compact expandable entry cards
  - Neural Archive (KB): per-document Download + Delete buttons
  - Neural Baseline moved to Settings modal as new tab

**Settings Modal**
- API Credentials: per-provider cards with key input + model visibility checkboxes
- Neural Baseline: custom system prompt textarea
- New tab: `baseline` with `Brain` icon

**Message Bubbles**
- User bubble: `bg-white/[0.07]` (removed pure white)
- Assistant bubble: transparent background
- "revised" amber badge when self-correction changed the response

**Workshop Page** (`/chat/workshop`)
- Renamed from "Knowledge Base" (`/chat/documents`)
- Document list with status indicators, upload, download, delete

**Stores / Hooks**
- `useContextExtractorStore` — tracks extraction state (idle/extracting/synced)
- `useDownloadDocument` — blob download via `<a>` click
- `useContextStore` — RAG chunk accumulator per message

---

## Numbers

| Metric | Value |
|---|---|
| New backend files | ~15 |
| New frontend files | ~8 |
| Modified files (total) | ~40+ |
| SSE chunk types | 8 (`token`, `reasoning`, `tool_call`, `tool_result`, `neural_context`, `correction`, `done`, `error`) |
| Built-in tools | 2 (`update_user_memory`, `save_context_entry`) |
| Skill executor skills | 3 (`web-search-searxng`, `web-reader`, `python-executor`) |
| LLM providers | 4 (Ollama, Anthropic, OpenAI, Google) |
| Qdrant collections | 2 (`documents`, `context_library`) |

---

## What Carries Forward to Phase 3

These were built in Phase 2 but are foundational for Phase 3:

- **ReAct loop** — the iterative reasoning engine Work Mode will build on
- **Langfuse observability** — traces will cover multi-agent runs
- **Self-Correction** — implemented but disabled in chat mode; will be activated as the Critic agent in Work Mode's Planner-Worker-Critic pipeline
- **`context_library`** — the shared memory that agents will read/write across Work Mode tasks
