# WO-013: Chat Interface & SSE Streaming
**To:** Frontend Agent
**Phase:** 1 (Walking Skeleton)
**PRD Reference:** §4 (Phase 1), §5.4
**Contract Reference:** Contract 2 (HTTP/SSE)

## Goal
Implement the end-to-end chat experience: conversation management in the sidebar and real-time streaming of AI responses in the main chat window.

## Acceptance Criteria
- [ ] **Conversation Management (Sidebar):**
    - Implement a sidebar that lists existing conversations (`GET /v1/conversations`).
    - Implement a "New Chat" button that creates a conversation (`POST /v1/conversations`) and switches to it.
    - Implement a delete action for conversations (`DELETE /v1/conversations/{id}`).
- [ ] **Message Thread (Main View):**
    - Implement a message list that renders historical messages (`GET /v1/conversations/{id}`).
    - Style messages distinctly: User (right-aligned, solid) and Assistant (left-aligned, glassmorphism).
- [ ] **Chat Composer & SSE Streaming:**
    - Implement a text input (`Composer`) with Cmd/Ctrl+Enter to send.
    - Implement a mutation that calls `POST /v1/conversations/{id}/messages` using the `sseStream` helper in `lib/sse.ts`.
    - **Streaming UI:** Tokens must appear in real-time as they arrive from the backend, not waiting for the full response.
    - Implement an "Abort" button (or Esc key) to cancel the current stream via `AbortController`.
- [ ] **UX Details:**
    - Auto-scroll to bottom upon new token arrival.
    - "Typing..." indicator while waiting for the first token.
    - Optimistic updates: show the user's message immediately before the API call completes.
- [ ] **Verification:**
    - Playwright E2E test: Type message $\to$ See stream $\to$ Reload page $\to$ Verify conversation and messages persist.

## Out of Scope
- AI-generated conversation titles (Phase 2).
- File uploads/RAG indicators (Phase 2).
- Work Mode agent graph (Phase 3).

## Hand-back Format
- All files committed to `/frontend`.
- Updated `CHANGELOG.md`.
- A "User Guide" snippet in `README.md` on how to start the first chat.
- Verified that the "streaming" feel is fluid and matches the Rain visual identity.
