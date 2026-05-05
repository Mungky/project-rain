# WO-021: Implement RAG Retrieval in Chat Orchestrator (REVISED)
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-22
**Priority:** high
**Phase:** 2
**PRD Reference:** §4 Phase 2, Milestone 2.5
**Contracts Touched:** Contract 2 (Backend ↔ Frontend HTTP)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
Before starting this Work Order, you MUST:
1.  Read your `backend/SYSTEM_PROMPT.md` to assume your identity as the Backend Agent.
2.  Read your `backend/INSTRUCTIONS.md` for your specific operational procedures.
3.  Install all skills located in the `backend/skills/` directory (e.g., `async-fastapi-patterns`, `pydantic-schema-author`, etc.) to use your specialized tools.

## Goal
Integrate RAG (Retrieval Augmented Generation) into the chat orchestrator so the LLM can answer questions based on uploaded documents.

## Context
Documents are now successfully chunked and embedded in Qdrant (WO-019). The next step is to query Qdrant during a chat session and provide the retrieved context to the language model. 

**Note for Agent:** A partial implementation exists but contains a critical async bug (missing `await`) and needs completion.

## Acceptance Criteria
- [ ] Update `backend/src/rain_backend/api/v1/messages.py` to inject the `qdrant_client` dependency (use `get_qdrant` dep) and pass it to `run_chat`.
- [ ] In `backend/src/rain_backend/orchestrator/chat_mode.py`, update `run_chat` signature to accept `qdrant_client`.
- [ ] **BUG FIX**: Ensure you `await` the Ollama provider's `embed()` method (e.g., `query_vector = (await providers["ollama"].embed([user_message]))[0]`).
- [ ] Query the Qdrant `documents` collection with the resulting vector to retrieve the top 3-5 most relevant chunks. Ensure filtering by `user_id` (use `DEFAULT_USER_ID` from `conversation_service`).
- [ ] Add a new RAG system prompt template in `backend/src/rain_backend/orchestrator/prompt_templates.py` that includes the provided context and instructs the model to say "I don't know" if the answer isn't in the context.
- [ ] Format the retrieved chunks into a text block and inject it as a `system` message before calling the provider.
- [ ] Extract unique `source` names (citations) from the retrieved Qdrant points' payloads.
- [ ] Include these citations in the `data` field of the final `done` SSE chunk (e.g., `{"message_id": "...", "usage": "...", "citations": ["file1.md", "file2.pdf"]}`).
- [ ] Graceful fallback: If Qdrant search fails or returns no chunks, continue the chat without the RAG system message.
- [ ] Unit tests for the modified `run_chat` and retrieval logic using mocks.
- [ ] CHANGELOG.md entry appended.

## Out of Scope
- Frontend UI rendering of citations.
- Work Mode / Planner (Phase 3).

## Dependencies
- Blocked by: WO-019 (Document Upload Pipeline), WO-020 (Dependencies)
- Blocks: none

## Hand-back
Standard.
