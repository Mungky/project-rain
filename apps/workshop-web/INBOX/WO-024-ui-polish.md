# WO-024: Implement Chat UI/UX Polish
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (UI/UX Polish)
**PRD Reference:** §4 Phase 2, Milestone 2.10
**Contracts Touched:** Contract 2 (Backend ↔ Frontend HTTP)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
Before starting this Work Order, you MUST:
1.  Read your `frontend/SYSTEM_PROMPT.md` to assume your identity as the Frontend Agent.
2.  Read your `frontend/INSTRUCTIONS.md` for your specific operational procedures.
3.  Install all skills in `frontend/skills/` (e.g., `streaming-chat-ui`, `rain-visual-identity`, etc.).

## Goal
Implement the user-requested UI features: Thinking Process, Thumbs Up/Down, Copy Button, and Edit Prompt.

## Context
The Backend and DB are now ready (WO-022, WO-023). We need to update the chat interface to consume the new `reasoning` SSE chunks and provide interactive elements for feedback and message management.

## Acceptance Criteria
- [ ] **Thinking Process**:
    - Update `lib/sse.ts` or the message stream consumer to handle the `reasoning` chunk type.
    - Create a `<ThinkingBlock>` component (collapsible/foldable) that displays the streamed reasoning content.
    - It should appear above the main assistant response.
- [ ] **Feedback Buttons**:
    - Add Thumbs Up and Thumbs Down icons to assistant messages in `message-bubble.tsx`.
    - Hook them up to the `PUT /v1/messages/{id}/feedback` endpoint.
    - Highlight the active rating (e.g., solid color for selected).
- [ ] **Copy Button**:
    - Add a "Copy" icon button to all messages (user and assistant).
    - Implement the "copy to clipboard" logic with a brief "Copied!" tooltip or state change.
- [ ] **Edit Prompt**:
    - Add an "Edit" icon to user messages.
    - When clicked, turn the message into an input field or populate the main composer with the content.
    - Resubmitting should trigger a new message stream (branching logic or simple resubmit is acceptable for Phase 2).
- [ ] **Visual Identity**:
    - Ensure all buttons follow the Rain glassmorphism style (deep blue/slate, subtle blurs).
- [ ] Update `use-send-message.ts` to handle the new stream types if necessary.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
