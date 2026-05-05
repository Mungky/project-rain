# WO-038: Dynamic Dashboard and 3-Section Info Panel
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Patenkan)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `frontend/SYSTEM_PROMPT.md`.
2.  Install all skills in `frontend/skills/`.

## Goal
Revamp the initial chat screen and build the right-side info panel to display Usage, Knowledge Base, and Neural Context.

## Acceptance Criteria
- [ ] **Dynamic Dashboard**:
    - Update `chat/page.tsx` (the empty state before selecting a chat).
    - Display the large Rain Logo, a warm welcome message, and 4 "Suggest Prompt" buttons (e.g., "Search the web for...", "Analyze my documents").
- [ ] **3-Section Right Panel**:
    - Update `components/chat/info-panel.tsx`:
        1. **Usage Section**: Display current token usage and model name.
        2. **Neural Archive**: Show list of uploaded documents (Fetch from `GET /v1/documents`).
        3. **Neural Context**: Display text snippets retrieved from the `neural_context` SSE chunk (from WO-037).
- [ ] **Agent Settings Page**:
    - Build a page/modal to edit `user_preferences` (Custom System Prompt, User Facts).
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
