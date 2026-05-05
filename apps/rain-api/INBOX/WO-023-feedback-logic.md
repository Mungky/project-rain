# WO-023: Implement Feedback API and Reasoning Logic
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (UI/UX Polish)
**PRD Reference:** §4 Phase 2, Milestone 2.10
**Contracts Touched:** Contract 2 (Backend ↔ Frontend HTTP)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
Before starting this Work Order, you MUST:
1.  Read your `backend/SYSTEM_PROMPT.md` to assume your identity as the Backend Agent.
2.  Read your `backend/INSTRUCTIONS.md` for your specific operational procedures.
3.  Install all skills located in the `backend/skills/` directory (e.g., `async-fastapi-patterns`, etc.).

## Goal
Implement the feedback endpoint and update the chat orchestrator to extract model reasoning content.

## Context
The DB schema is now ready (WO-022). We need the API to accept feedback ratings and the orchestrator to detect when the model is "thinking" (e.g., using `<think>` tags) to store that content separately.

## Acceptance Criteria
- [ ] **Feedback Endpoint**: 
    - Add `PUT /v1/messages/{message_id}/feedback` in `api/v1/messages.py`.
    - Request body should accept a `feedback` integer (1, -1, or 0/null).
    - Update the message record in Postgres.
- [ ] **Reasoning Extraction**:
    - Update `orchestrator/chat_mode.py` to detect `<think>` tags in the streaming output from the LLM.
    - As tokens arrive, if they are inside a `<think>` block, accumulate them into `reasoning_content`.
    - When saving the assistant message to the DB, populate the `reasoning_content` column.
    - Strip the `<think>` block from the final `content` stored in the DB (so the main message only contains the actual answer).
- [ ] **SSE Update**:
    - Add a new SSE chunk type: `{"type": "reasoning", "data": "..."}`.
    - Yield these chunks as the thinking process arrives, so the frontend can display them in real-time.
- [ ] Update `Message` Pydantic models in `schemas/conversation.py` to include the new fields.
- [ ] Unit tests for the feedback endpoint and the regex/logic for tag extraction.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
