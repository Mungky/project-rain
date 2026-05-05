# WO-035: Sync Frontend with Per-Conversation Model
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** medium
**Phase:** 2 (Refactor)
**PRD Reference:** §5.4 Frontend Role
**Contracts Touched:** Contract 2 (HTTP API)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `frontend/SYSTEM_PROMPT.md` and `frontend/INSTRUCTIONS.md`.
2.  Install skills in `frontend/skills/`.

## Goal
Update the conversation creation flow to send the selected model to the backend.

## Acceptance Criteria
- [ ] **Create Conversation**:
    - Update `hooks/use-conversations.ts` (specifically `useCreateConversation` mutation).
    - The `apiPost` call for creating a new conversation should now include the `selectedModelId` from the `useModelStore` in the request body.
- [ ] **Chat Logic**:
    - When sending a message (in `use-send-message.ts`), ensure it respects the model already assigned to the conversation (the backend will handle this, but frontend should avoid redundant model sending if no longer needed by the API).
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
