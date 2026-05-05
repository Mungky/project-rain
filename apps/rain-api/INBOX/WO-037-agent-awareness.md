# WO-037: Agent Awareness and Dynamic Context
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Patenkan)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `backend/SYSTEM_PROMPT.md`.
2.  Install all skills in `backend/skills/`.

## Goal
Update the orchestrator to make the AI aware of its Knowledge Base, use global preferences, and sync RAG context with the UI.

## Acceptance Criteria
- [ ] **Dynamic System Prompt**:
    - Update `chat_mode.py` to fetch `user_preferences` from DB.
    - Inject `custom_system_prompt` and `user_context` into the LLM starting prompt.
    - **Awareness**: Explicitly tell the AI it has a "Neural Archive" (Knowledge Base) and "Tools" (Search) in the system prompt.
- [ ] **Neural Context Sync**:
    - When RAG retrieves chunks from Qdrant, yield a new SSE chunk: `{"type": "neural_context", "data": [{"source": "file.txt", "text": "..."}]}`.
    - This allows the frontend's right panel to show what the agent is "reading" in real-time.
- [ ] **Refactor run_chat**:
    - Ensure it uses the `model` locked in the `Conversation` object (from WO-036).
    - Handle empty `custom_system_prompt` gracefully.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
