# WO-034: Implement Model-at-Conversation and Auto-Title Logic
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Refactor)
**PRD Reference:** §5.2 Backend Role
**Contracts Touched:** Contract 2 (HTTP API), Contract 3 (Postgres)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `backend/SYSTEM_PROMPT.md` and `backend/INSTRUCTIONS.md`.
2.  Install skills in `backend/skills/`.

## Goal
Update the API and orchestrator to support per-conversation model locking and automatic title generation from the first assistant response.

## Acceptance Criteria
- [ ] **API Update**:
    - Update `POST /v1/conversations` (in `api/v1/conversations.py`) to accept a `model` string in the request body.
    - Update `ConversationService.create_conversation` to save this model to the database.
- [ ] **Orchestrator Update (`chat_mode.py`)**:
    - Retrieve the model name from the `Conversation` object instead of the message request body.
    - **Auto-Title Logic**: After the **first** assistant message is generated:
        1. Check if the conversation `title` is currently null or generic (e.g., "New Conversation").
        2. If it is the first assistant message, take the first 30 characters of the content.
        3. Clean up the snippet (remove newlines, trailing spaces).
        4. Update the `title` column in the `conversations` table.
        5. Commit to DB.
- [ ] **Message Service**:
    - Update `create_message` to no longer require/save the `model` column (since it's now in the conversation).
- [ ] Update Pydantic schemas in `schemas/conversation.py` to match the new DB structure.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
