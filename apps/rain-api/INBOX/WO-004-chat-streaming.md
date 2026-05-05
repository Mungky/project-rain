# WO-004: Chat Streaming Endpoint
**To:** Backend Agent
**Phase:** 1
**PRD Reference:** §4 (Phase 1), §5.2, §6 (Match Opus Strategy)
**Contract Reference:** Contract 2 (HTTP/SSE), Contract 7 (Provider Adapter)

## Goal
Implement the core chat loop: retrieving conversation history, calling the Ollama provider, streaming the response via SSE, and persisting the final message to the database.

## Acceptance Criteria
- [ ] Implement `POST /v1/conversations/{id}/messages` as a Server-Sent Events (SSE) stream.
- [ ] Implement the linear orchestration flow in `orchestrator/chat_mode.py`:
    1. Load conversation history from Postgres.
    2. Construct the prompt using a system template (per `prompt-engineering-for-tiny-models` skill).
    3. Call the `Provider.chat()` method to get an async iterator of chunks.
    4. Stream chunks to the client using the SSE envelope: `{"type": "token", "data": "..."}`.
    5. Persist the final assistant response and token counts to the `messages` table.
- [ ] Implement the `streaming/sse.py` helper to ensure the JSON envelope is strictly followed per Contract 2.
- [ ] Implement error handling: if the LLM fails, stream an `{"type": "error", "data": {...}}` chunk.
- [ ] Ensure the endpoint handles `AbortController` (client disconnection) by canceling the provider request.
- [ ] Integration test: Full E2E flow with real Ollama instance (Send message $\to$ See tokens stream $\to$ Verify DB persistence).

## Out of Scope
- RAG retrieval (Phase 2).
- Complexity-based routing (Phase 3).
- Multimodal inputs (Phase 4).

## Hand-back Format
- All files committed to `/backend`.
- Updated `CHANGELOG.md` with detailed entries.
- Verified that the streaming endpoint works end-to-end and handles disconnections gracefully.
