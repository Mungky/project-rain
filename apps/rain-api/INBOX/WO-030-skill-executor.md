# WO-030: Implement Skill Executor and Tool Use Loop
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** blocker
**Phase:** 2 (Final Milestone)
**PRD Reference:** §4 Phase 2, Milestone 2.8
**Contracts Touched:** Contract 6 (Skill Manifest), Contract 7 (Provider Tools)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `backend/SYSTEM_PROMPT.md`.
2.  Read `backend/INSTRUCTIONS.md`.
3.  Install skills in `backend/skills/`.

## Goal
Enable Rain to execute external skills (tools) by implementing a sandboxed executor and integrating it into the chat orchestrator.

## Context
We have the CLI to install skills (WO-029). Now we need the runtime to execute them. For safety, skills MUST run in a sandboxed environment (Python `subprocess` or `docker`). *Requirement for Phase 2: Simple Subprocess with timeout is acceptable, Docker is preferred if feasible.*

## Acceptance Criteria
- [ ] **Skill Service**:
    - Create `backend/src/rain_backend/services/skill_service.py` to manage skill registration and discovery from the database.
- [ ] **Skill Executor**:
    - Create `backend/src/rain_backend/skills/executor.py`.
    - Implement a function `execute_skill(skill_id, inputs)` that:
        - Loads the skill's `manifest.yaml` and `handler.py`.
        - Runs the `handle()` function in a separate process with a strict timeout (e.g., 30s).
        - Captures and returns the result or error.
- [ ] **Tool-Use Loop in Orchestrator**:
    - Update `orchestrator/chat_mode.py` to:
        - Fetch all "enabled" skills from the DB.
        - Convert skill manifests into the standard "Tool" format (JSON Schema) for LLM providers.
        - Pass these tools to the provider's `chat()` call.
        - **Handle Tool Calls**: If the LLM returns a `tool_call` chunk:
            1. Emit a `tool_call` SSE chunk to the frontend.
            2. Call `execute_skill`.
            3. Emit a `tool_result` SSE chunk with the output.
            4. Send the result back to the LLM for a final response generation.
- [ ] **SSE Update**:
    - Ensure `ChatChunk` supports `tool_call` and `tool_result` types (already in schema).
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
