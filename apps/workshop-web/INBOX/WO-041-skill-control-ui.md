# WO-041: Skill Control Center and Neural Context UI
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** blocker
**Phase:** 2 (Patenkan - UI/UX)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1. Read `frontend/SYSTEM_PROMPT.md`.
2. Install all skills in `frontend/skills/`.

## Goal
Build the "Skill Control Center" in the right Info Panel and visualize the Neural Context (RAG) stream.

## Acceptance Criteria
- [ ] **SSE Stream Update**:
    - Update `use-send-message.ts` and `sse.ts` to listen for the `neural_context` chunk type.
    - Store this context in a new global store (e.g., `useContextStore`) or within the conversation state so the Info Panel can read it.
- [ ] **InfoPanel Revamp**: Update `components/chat/info-panel.tsx` to include:
    - **Usage**: (Existing)
    - **Neural Archive**: (Existing - List of files)
    - **Neural Context**: A new section showing the live text snippets retrieved by RAG (from the SSE stream).
    - **Reference**: A text area to input custom system prompts (`custom_system_prompt`), saved via `user_preferences` API (you may need to mock the API save if not fully implemented in backend yet, or just bind it to local state for now).
    - **SKILLS**: 
        - A search bar to filter skills.
        - A master **AUTO** toggle (controls `conversation.auto_skills`).
        - A list of installed skills (fetch from `GET /v1/skills`).
        - Each skill has a toggle switch aligned to the right.
        - If AUTO is ON, all individual skill toggles should be visually disabled/greyed out but still reflect their underlying state.
- [ ] **Sync with Backend**:
    - Ensure toggling skills or changing the AUTO switch triggers a `PATCH /v1/conversations/{conversationId}` call to save the state.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
