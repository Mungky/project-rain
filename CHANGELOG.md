## [2026-04-24] Frontend + Backend — WO-054: Clean Attachment UX + Fix Model Revert to Kimi
- **Attachment UX**: File content no longer shown in the chat bubble. Backend now accepts `attachments: [{name, content}]` as a separate field in `PostMessageRequest`. `chat_mode.py` builds the LLM prompt with attachment content prepended (`[Attached: name]\n\`\`\`...\`\`\``) but stores only the user's typed text in DB. Frontend sends `content` (typed text) and `attachments` separately. During streaming, the user message bubble shows file name chips below the text; after DB fetch, the typed message is shown clean.
- **Bug Fix (model revert)**: `model-selector.tsx` auto-select `useEffect` was re-running every time the models query was invalidated (e.g. after saving API keys), resetting the selected Gemini/GPT model back to the first model (kimi). Fix: auto-select now only fires when `selectedModelId` is empty (first-time load), never overriding an existing selection.

## [2026-04-24] Frontend + Backend — WO-053: Fix Model Defaulting to Kimi + Attachment Binary Validation
- **Bug Fix (Model)**: `model-store.ts` storage renamed from `rain-model-storage` → `rain-model-storage-v2`, clearing stale persisted `"kimi-k2.6:cloud"` default from localStorage. Default `selectedModelId` is now `""`. `model-selector.tsx` auto-selects first available model when nothing is selected. `chat_mode.py` now treats empty string the same as `None` (prevents empty model being saved to DB). `composer.tsx` send button disabled and `send()` bails out if no model is selected.
- **Bug Fix (Attachment)**: `.docx`, `.pdf`, and other binary formats are now rejected with a user-facing error message. Extension validation runs before `file.text()` is called — only extensions in `ALLOWED_EXTENSIONS` (txt, md, py, js, ts, json, csv, etc.) are accepted.

## [2026-04-24] Backend + Frontend — WO-052: No. 1 Tool Visibility + No. 4 Attachment + OpenAI Bug Fix + No. 2 Model Registry
- **Bug Fix (OpenAI/Anthropic/Google)**: `chat_mode.py` now falls back to user's DB-stored API key when startup providers are not initialized (e.g., no env var). Covers the case where user adds key via Settings UI without setting env vars. Error message improved: now shows "No API key configured for {provider}. Please add one in Settings."
- **No. 2 — Model Registry**: Created `providers/model_registry.py` as single source of truth for all model IDs. Each provider's `list_models()` now reads from `MODEL_REGISTRY` — update one file to add/remove models across the whole system.
- **No. 1 — Tool Call Visibility**: `use-send-message.ts` now handles `tool_call` and `tool_result` SSE chunks, storing them as `tool_events` on the optimistic message. `message-bubble.tsx` renders each tool event as a compact pill showing tool name + spinner (calling) or green lightning bolt (done).
- **No. 4 — In-Context Attachment**: Composer `+` button now opens a file picker (txt, md, py, js, ts, tsx, json, csv, etc.). Selected files are shown as chips inside the composer. On send, file content is prepended to the message as a fenced code block: `[Attached: filename]\n\`\`\`\n{content}\n\`\`\``. Multiple files supported. Send button activates even with attachment and no text.

## [2026-04-24] Frontend — WO-049: Fix Model Bleeding Between Conversations
- **Bug**: Old conversations would "inherit" the model from newer conversations. Root cause: `Composer.tsx` never passed `model` to `useSendMessage`, so it always fell back to `useModelStore.selectedModelId` (global, persisted state). If user had switched to "gpt" for a new session while an old "gemini" session existed, the next message in the gemini session would be sent as gpt — overwriting `conversation.model` in DB via the `model != conversation.model` update path in `chat_mode.py`.
- **Fix** `composer.tsx`: compute `effectiveModel = !isCentered && forcedModelId ? forcedModelId : selectedModelId`. Existing conversations (`!isCentered`) lock to their stored model; new sessions use the global dropdown selection. Pass `effectiveModel` to `mutate({ model: effectiveModel })`.

## [2026-04-24] Backend + Frontend — WO-048: Per-Model Agent Toggle (No. 3 revised)
- **Backend UPDATE** `api/v1/user.py`: removed provider-level enabled toggle from UI contract. Added `hidden_models: list[str]` field to `PreferencesResponse` + `PreferencesUpdate`. PATCH now persists `hidden_models` inside `api_keys` JSONB. Saving an API key auto-sets `enabled: true` for that provider.
- **Backend UPDATE** `api/v1/models.py`: reads `hidden_models` set from DB. Each model now returns `enabled = model_id not in hidden_models`. All models returned (not filtered), so frontend can render checkboxes.
- **Backend UPDATE** `schemas/common.py`: `ModelResponse.enabled: bool = True` already added in WO-047.
- **Frontend UPDATE** `api-types.ts`: `ModelResponse` gains `enabled: boolean`. `UserPreferencesResponse` gains `hidden_models: string[]`.
- **Frontend UPDATE** `use-user-preferences.ts`: `UpdatePreferencesPayload` gains `hidden_models?: string[]`.
- **Frontend UPDATE** `settings-modal.tsx`: removed per-provider toggle switch. Each provider card now always shows API key input + [Save]. Model checkboxes appear below (checked = visible in dropdown). Saving a key or toggling a model invalidates the models query.
- **Frontend UPDATE** `model-selector.tsx`: dropdown now filters `models.filter(m => m.enabled)` — only checked models appear.
- **Verified design**: Settings → API Credentials → provider cards with key input → model checkboxes below each.

## [2026-04-24] Backend + Frontend — WO-047: Provider Settings (No. 3)
- **Backend NEW** `api/v1/user.py`: `GET /v1/user/preferences` + `PATCH /v1/user/preferences`. Stores provider configs in `user_preferences.api_keys` JSONB. All 4 providers: anthropic, openai, google, ollama.
- **Backend UPDATE** `api/v1/models.py`: reads enabled/disabled state + user API keys from DB at request time. Builds fresh provider instance if user has stored key. Only returns models from enabled providers.
- **Frontend UPDATE** `api-types.ts`: new `ProviderConfig` + `UserPreferencesResponse` shape.
- **Frontend UPDATE** `use-user-preferences.ts`: new `UpdatePreferencesPayload` type for flexible partial PATCH.
- **Frontend UPDATE** `settings-modal.tsx`: replaced flat key inputs with 4 provider cards — each has toggle switch, API key/URL input, eye toggle, per-provider save with success feedback.
- **Verified**: enabling/disabling a provider immediately changes the model dropdown list.

## [2026-04-24] Parent — WO-046: SearXNG + General-Purpose Skills
- **Infrastructure**: Added `rain-searxng` container to `docker-compose.yml` (port 8080). Config at `searxng/settings.yml` — Google, Bing, DDG, Wikipedia aggregated, JSON format enabled.
- **Skill `web-search-searxng` v1.0.0**: Replaces DuckDuckGo. Calls SearXNG JSON API, deduplicates results, returns [{title, url, snippet, source}].
- **Skill `web-reader` v1.0.0**: Fetches full webpage text from any URL. Stdlib-only (urllib + html.parser). Strips scripts/nav/footer, returns clean text up to configurable max_chars. Enables scraping + deep summarization.
- **Skill `python-executor` v1.0.0**: Runs Python code in isolated subprocess with timeout (max 30s). Returns stdout/stderr/returncode. Enables calculations, data processing, any computational task.
- **Backend**: Added `POST /v1/skills/sync` endpoint for on-demand registry sync without restart.
- **Verified**: AI correctly used `web-search-searxng` for Bitcoin price query, returned IDR price from live Indonesian crypto sources.

## [2026-04-24] Backend — WO-045: Session 1 — Fix Tool Execution & Activate Episodic Memory
- **Bug fix**: Added missing `from datetime import datetime` in `chat_mode.py` — all prompts were crashing.
- **Bug fix**: Added missing `from sqlalchemy import select` — preference fetch was silently failing.
- **Bug fix**: Fixed `tool_args` NameError — all skill execution was dead, now extracts from `tool_call["args"]`.
- **Bug fix**: Fixed `ChatRequest.messages` type from `dict[str, str]` to `dict[str, Any]` in `providers/base.py` — tool_call messages were rejected by Pydantic.
- **Bug fix**: Fixed `enabled_skills` filter — compared names against UUIDs, now supports both UUID and name matching.
- **Bug fix**: Corrected tool message reconstruction for Ollama re-submission format.
- **Feature**: Added `PreferenceService` (`services/preference_service.py`) — upserts key-value pairs into `user_preferences.user_context` JSON blob with legacy plain-text migration.
- **Feature**: Added built-in `MEMORY_TOOL` — AI can now silently call `update_user_memory` to persist user facts across sessions without user intervention.
- **Feature**: System prompt now renders `user_context` as a formatted bullet list instead of raw JSON.
- **Verified**: Web search end-to-end working. Episodic memory saving to DB confirmed.

## [2026-04-23] Parent — Phase 2 closed
- **Goal reached**: Documents are queryable via RAG, Skill Ecosystem is functional with a live DuckDuckGo search tool, and Hosted Providers (Anthropic, OpenAI, Google) are integrated.
- **What shipped**:
    - **Memory**: Qdrant vector storage, MinIO object storage, and automated document processing pipeline (chunking/embedding).
    - **Skills**: CLI `skills.sh`, Skill Executor runtime, and the `web-search-duckduckgo` skill.
    - **Providers**: Adapters for Claude 3.5, GPT-4o, and Gemini 1.5 Pro.
    - **UI/UX**: Model selector dropdown, Knowledge Base management UI, real-time reasoning display, feedback buttons, and copy/edit functionality.
- **Phase progress**: 100% of Phase 2.
- **Next**: Opening Phase 3 (Work Mode & Orchestration).

## [2026-04-23] Backend — WO-040: Dynamic Skill Filtering and Context Awareness
- Implemented logic in `chat_mode.py` to fetch and inject `UserPreference` (`custom_system_prompt` and `user_context`) into the LLM system prompt.
- Added dynamic skill filtering: tools passed to the LLM are now constrained by `conversation.auto_skills` and `conversation.enabled_skills`.
- Added `neural_context` SSE chunk yield during RAG retrieval to sync context with the UI.
- Implemented `PATCH /v1/conversations/{id}` to allow updating session settings (model, title, skills).
- Created `GET /v1/skills` endpoint to list installed skills.
- Phase progress: ~65% of Phase 2 (Patenkan - Logic Ready).

## [2026-04-23] DB — WO-039: Session-Specific Skill Configuration
- Updated `Conversation` model with `auto_skills` (Boolean) and `enabled_skills` (JSONB) for granular control.
- Created `UserPreference` model to store custom system prompts, user contexts, and API keys.
- Applied Alembic migration `b1d26d39f399` to synchronize session skill configurations.
- Phase progress: ~60% of Phase 2 (Patenkan - Infrastructure Ready).

## [2026-04-23] Backend — WO-027: Hosted Provider Adapters
- Implemented `AnthropicProvider`, `OpenAIProvider`, and `GoogleProvider` adapters following Contract 7.
- Added support for Claude 3.5, GPT-4o, and Gemini 1.5 Pro models.
- Implemented `GET /v1/models` for a unified list of all available models across local and hosted providers.
- Integrated new providers into the app lifespan and `build_providers` factory.
- Phase progress: ~95% of Phase 2 (Hosted providers integrated).

## [2026-04-23] Frontend — WO-026: Document Management UI
- Created `Knowledge Base` management page at `/chat/documents`.
- Implemented `useDocuments`, `useUploadDocument`, and `useDeleteDocument` hooks with TanStack Query.
- Added file upload functionality with support for `.txt` and `.md` files.
- Added document listing with real-time status polling for background processing.
- Added document deletion with multi-store cleanup integration.
- Integrated `Knowledge Base` link into the sidebar navigation.
- Phase progress: ~90% of Phase 2.

## [2026-04-23] Backend — WO-025: Document List and Delete API
- Implemented `GET /v1/documents` for paginated listing of uploaded files.
- Implemented `DELETE /v1/documents/{id}` for complete cleanup across Postgres, MinIO, and Qdrant.
- Updated `DocumentService` with multi-store deletion logic and atomicity handling.
- Standardized `DocumentListResponse` and `DocumentResponse` schemas.
- Phase progress: ~85% of Phase 2 (Document management base complete).

## [2026-04-24] Parent — Phase 3 started
- **Goal**: Implement Work Mode with multi-agent orchestration (Planner-Worker-Critic) and 4-tier memory.
- **Work orders issued**: 
    - DB Agent (WO-044): Agent Run & Task schemas.

## [2026-04-24] Parent — Phase 2 closed
- **Final Result**: Rain is now a "Proper Agent" with real-world awareness, DuckDuckGo search integration, and robust RAG capabilities.
- **Key fixes**: Resolved LLM date hallucination and fixed Skill Executor pathing.
- **Phase progress**: 100% of Phase 2.

## [2026-04-23] Frontend — WO-024: Chat UI/UX Polish
- Implemented `<ThinkingBlock>` component to display model reasoning in real-time.
- Added **Thumbs Up/Down** feedback buttons to assistant messages, integrated with the backend API.
- Added **Copy** button with clipboard functionality and visual "Copied" feedback.
- Added **Edit** button to user messages for quick prompt revision.
- Standardized terminology to **`reasoning`** across the system (Backend chunks, DB columns, and Frontend hooks).
- Phase progress: ~80% of Phase 2.

## [2026-04-23] Backend — WO-023: Feedback API and Reasoning Logic
- Added `PUT /v1/messages/{id}/feedback` endpoint to handle user ratings.
- Implemented real-time `<think>` tag parsing in chat orchestrator.
- Added `reasoning` SSE chunk type to stream model thinking process separately.
- Updated `Message` model and service to persist `reasoning_content` and `feedback`.
- Phase progress: ~65% of Phase 2 (UI/UX Polish backend ready).

## [2026-04-23] DB — WO-022: Add Feedback and Reasoning to Messages
- Updated `Message` model with `feedback` (integer) and `reasoning_content` (text) columns.
- Applied Alembic migration `3c737a5a064e` with explicit SQL comments and `TIMESTAMPTZ` compliance.
- Phase progress: ~55% of Phase 2 (UI/UX Polish base ready).

## [2026-04-23] Backend — WO-021: RAG Retrieval in Chat Orchestrator
### Added
- RAG (Retrieval-Augmented Generation) integration in chat: embed user query, search Qdrant, inject context as system message.
- `RAG_SYSTEM_PROMPT` template in `orchestrator/prompt_templates.py` with context injection and citation rules.
- `build_rag_messages()` function to build messages with RAG context using temperature 0.3 for factual Q&A.
- Qdrant retrieval in `run_chat()`: top-5 chunks, filtered by `user_id`, graceful fallback if Qdrant unavailable.
- Citations in SSE `done` chunk: `data["citations"]` array with source filenames from retrieved documents.
- 5 new unit tests in `test_chat_mode.py`: RAG context flow, Qdrant unavailable, empty results, search failure, citations in done chunk.
- **Contract conformance**: Contract 2 (SSE streaming with citations), Contract 4 (Qdrant payload schema).
- Phase progress: ~50% of Phase 2 (Memory & Skills).

## [2026-04-22] Backend — WO-019: Document Upload Pipeline
### Added
- `POST /v1/documents` endpoint accepting multipart file uploads (text/plain, text/markdown).
- `DocumentService` with full pipeline: MinIO storage → text extraction → chunking (~512 tokens) → Ollama embedding (nomic-embed-text) → Qdrant upsert.
- `schemas/document.py` with `DocumentUploadResponse` and `DocumentResponse` using `UTCDatetime`.
- MinIO client initialization in app lifespan with `asyncio.to_thread` wrapping.
- Qdrant `AsyncQdrantClient` initialization with auto-creation of `documents` collection (768-dim, Cosine, int8 quantization).
- `get_minio` and `get_qdrant` dependencies in `api/deps.py`.
- `minio_bucket_uploads` and `minio_secure` settings.
- 23 unit tests covering chunking logic, upload success, and all error paths (MIME, MinIO, embedding, Qdrant, decode failures).
- **Contract conformance**: Contract 2 (POST /v1/documents), Contract 4 (Qdrant payload schema).
- Phase progress: ~30% of Phase 2.

## [2026-04-22] Backend — Fix missing dependencies for document uploads
- Added `python-multipart` to `pyproject.toml` and synchronized virtual environment.
- Resolved "Unprocessable Content" error when handling multipart file uploads.
- Phase progress: 40% of Phase 2.

## [2026-04-22] Backend — Implement Document Upload Pipeline
- Created `POST /v1/documents` endpoint for multipart file uploads.
- Implemented `DocumentService` for text chunking and embedding using `nomic-embed-text`.
- Integrated MinIO for raw file storage and Qdrant for vector storage.
- Added automatic Qdrant collection initialization in app lifespan.
- Phase progress: 35% of Phase 2.

## [2026-04-22] DB — Create Document and Skill schemas
- Created `Document`, `Skill`, and `SkillExecution` SQLAlchemy models.
- Applied Alembic migration `3c737a5a064d` for Phase 2 entities.
- Phase progress: 20% of Phase 2.

## [2026-04-22] DB — Set up Qdrant and MinIO
- Added `qdrant` and `minio` services to `docker-compose.yml` with health checks.
- Created `db/qdrant_collections.yaml` with `documents` collection definition (768 dim, int8 quantization).
- Created `db/seeds/seed_minio_buckets.py` to initialize `rain-uploads` and `rain-skill-artifacts`.
- Synchronized root `.env.example` with new datastore connection strings.
- Phase progress: 10% of Phase 2.

## [2026-04-22] Parent — Phase 1 closed
- **Goal reached**: End-to-end chat works with local Ollama (`kimi-k2.6:cloud`), persisted to Postgres with `TIMESTAMPTZ`, streamed to a Rain-themed UI.
- **What shipped**:
    - Backend: FastAPI skeleton, SSE streaming, Ollama provider, Conversation/Message services with async SQLAlchemy 2.x.
    - DB: Postgres schema with migrations, Redis (caching ready).
    - Frontend: Next.js 16 scaffold, Chat Mode UI, Zustand/TanStack Query integration.
- **Note**: Phase 1 was extended to resolve critical datetime offset issues and model availability. All 5 Definition-of-Done items are green.
- **Phase progress**: 100% of Phase 1.
- **Next**: Opening Phase 2 (Memory & Skills) with requested UI enhancements.

## [2026-04-22] - WO-016: Resolve Datetime Offset Conflict (Backend)
### Fixed
- Added `UTCDatetime` annotated type in `schemas/common.py` using `AfterValidator` to ensure all `datetime` fields are UTC-aware — even naive datetimes from the DB are automatically converted.
- Updated `schemas/conversation.py` to use `UTCDatetime` for all datetime fields (`created_at`, `updated_at`, `deleted_at`) across `Message`, `Conversation`, `ConversationResponse`, and `ConversationCreatedResponse`.
- Verified RFC3339-compliant JSON serialization: all datetime outputs include `+00:00` or `Z` suffix.
- Fixed cursor pagination in `conversation_service.py`: `datetime.fromisoformat(cursor)` now ensures timezone-aware result.
- Fixed typo in `conversation_service.py`: `Conversation_model` → `ConversationModel`.
- Added 16 unit tests in `tests/unit/test_datetime_awareness.py` covering naive-to-aware conversion, RFC3339 serialization, cursor parsing, and schema validation.
- **Contract conformance**: Contract 3 (Backend ↔ Postgres) verified — backend now fully compatible with `TIMESTAMPTZ` columns from WO-015 migration.

---

## [2026-04-22] - CRITICAL BUG: Datetime Offset Conflict (RESOLVED)
### Status: FIXED
- **Issue**: `sqlalchemy.exc.DBAPIError` (can't subtract offset-naive and offset-aware datetimes).
- **Fix**: Schema updated to aware timestamps (`TIMESTAMPTZ`) via explicit `DateTime(timezone=True)` in models.
- **Migration**: Applied manual Alembic migration `51d480acf766` with `ALTER COLUMN ... TYPE TIMESTAMPTZ`.
- **Backend**: Verified all services use `UTC` aware datetimes and handle naive cursor inputs safely.

---

## [2026-04-22] - API Route Synchronization

### Fixed
- Synchronized Frontend API calls with new explicit Backend routes.
- Update `use-conversations.ts`: `GET /v1/conversations` $\to$ `/v1/conversations/list`.
- Update `use-conversations.ts`: `POST /v1/conversations` $\to$ `/v1/conversations/create`.
- Resolved potential 404/405 errors caused by route ambiguity.
