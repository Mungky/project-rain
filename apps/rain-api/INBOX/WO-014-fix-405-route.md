# WO-014: BUG FIX - Conversation POST Method Not Allowed (405)
**To:** Backend Agent
**Phase:** 1 (Walking Skeleton - Bug Fix)
**PRD Reference:** §4 (Phase 1)
**Contract Reference:** Contract 2 (HTTP)

## Goal
Resolve the `405 Method Not Allowed` error occurring when the frontend attempts to create a new conversation via `POST /v1/conversations`.

## Acceptance Criteria
- [ ] **Route Audit:** 
    - Review `backend/src/rain_backend/api/v1/conversations.py`.
    - Ensure the a dedicated `@router.post("/")` (or `@router.post("")`) exists for conversation creation and is not accidentally defined as a `@router.get`.
- [ ] **Trailing Slash Resolution:** 
    - Verify if the issue is caused by a trailing slash redirect (FastAPI redirects `/v1/conversations/` to `/v1/conversations` but may drop the POST method). Ensure the route definition and the frontend call match exactly.
- [ ] **Method Verification:** 
    - Test the endpoint using `curl` or Swagger UI (`/docs`) to confirm that `POST /v1/conversations` returns a `201 Created` or `200 OK`, not a `405`.
- [ ] **CORS/Middleware Check:** 
    - Verify that `CORSMiddleware` is correctly configured to allow `POST` methods from the frontend origin.

## Hand-back Format
- Fix committed to `/backend`.
- Updated `CHANGELOG.md` with a "BUG FIX" entry detailing the cause of the 405 error.
- Log proof of a successful `POST` request to `/v1/conversations`.

## Warning
This is a blocking bug for Phase 1. The "Walking Skeleton" cannot be completed if the user cannot start a conversation. High priority.
