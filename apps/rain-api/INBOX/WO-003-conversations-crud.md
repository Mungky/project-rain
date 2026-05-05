# WO-003: Conversations CRUD
**To:** Backend Agent
**Phase:** 1
**PRD Reference:** §4 (Phase 1), §5.2
**Contract Reference:** Contract 2 (HTTP), Contract 3 (Postgres)

## Goal
Implement the full set of REST endpoints for managing conversations (CRUD) with soft delete support.

## Acceptance Criteria
- [ ] Implement the following endpoints per Contract 2:
    - `POST /v1/conversations`: Create a new conversation, return `{id, created_at}`.
    - `GET /v1/conversations`: List all non-deleted conversations for the user.
    - `GET /v1/conversations/{id}`: Retrieve a full conversation including its messages.
    - `DELETE /v1/conversations/{id}`: Implement soft delete via `deleted_at` column.
- [ ] Use Pydantic models for all request/response DTOs (refer to `pydantic-schema-author` skill).
- [ ] Implement a service layer to decouple API endpoints from database logic.
- [ ] Ensure all queries filter out soft-deleted records.
- [ ] Unit tests for all endpoints using mocked DB sessions (pytest).
- [ ] Integration tests verifying the full flow (Create $\to$ List $\to$ Retrieve $\to$ Delete $\to$ Verify missing from List).

## Out of Scope
- Chat streaming/message appending (Deferred to WO-004).
- User authentication (Phase 1 uses a single default user).
- Conversation title generation (AI-driven).

## Hand-back Format
- All files committed to `/backend`.
- Updated `CHANGELOG.md` with detailed entries.
- Verified that OpenAPI schema is updated and matches Contract 2.
