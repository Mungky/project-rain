# WO-040: Dynamic Skill Filtering and Context Awareness
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Patenkan - Skills Logic)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `backend/SYSTEM_PROMPT.md`.
2.  Install all skills in `backend/skills/`.

## Goal
Implement the logic to filter skills per session and inject user preferences into the chat context.

## Context
The DB is now ready (WO-039). The orchestrator must now respect the `auto_skills` and `enabled_skills` settings for each conversation and use the user's custom system prompt.

## Acceptance Criteria
- [ ] **Conversation Update API**:
    - Update `PATCH /v1/conversations/{conversation_id}` to allow updating `auto_skills` and `enabled_skills`.
- [ ] **Dynamic Prompt Injection**:
    - In `chat_mode.py`, fetch `UserPreference` for the current user.
    - If `custom_system_prompt` or `user_context` exists, append it to the base `SYSTEM_PROMPT`.
- [ ] **Skill Filtering**:
    - Update `run_chat` logic for tool selection:
        - If `conversation.auto_skills` is **True**: Pass all available skills to the provider's `tools` parameter.
        - If `conversation.auto_skills` is **False**: ONLY pass skills whose names are in `conversation.enabled_skills`.
- [ ] **Skill Search API**:
    - Ensure `GET /v1/skills` returns all installed skills from the registry/DB so the frontend can display them in the list.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
