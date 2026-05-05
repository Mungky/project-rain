# WO-045: Session 1 — Fix Tool Execution & Activate Episodic Memory
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-24
**Priority:** critical
**Phase:** 2

## Context
Chat mode has two blocking bugs and one missing capability:
1. `tool_args` NameError in `chat_mode.py` — all skill execution is dead
2. Tool message reconstruction uses wrong format for Ollama re-submission
3. Episodic memory exists in `user_preferences.user_context` but the AI cannot write to it

## Scope
All changes stay in `/backend`. Schema is not touched (UserPreference already has `user_context: Text`).

## Acceptance Criteria

### A. Fix tool_args NameError (chat_mode.py)
- Extract `tool_args = tool_call.get("args", {})` from chunk data
- Ollama yields `{"id", "name", "args"}` — this matches the fix

### B. Fix tool message reconstruction
- Assistant turn: `{"role": "assistant", "content": "", "tool_calls": [{"function": {"name": ..., "arguments": tool_args}}]}`
- Tool result turn: `{"role": "tool", "content": json.dumps(result)}`
- Remove incorrect `tool_call_id` and `name` fields that Ollama does not expect

### C. New file: `services/preference_service.py`
- `PreferenceService.update_memory(user_id, key, value)` — upsert one key into `user_context` JSON blob
- Handle legacy plain-text `user_context` gracefully (wrap in `{"notes": ...}`)
- Commit and return `{"status": "saved", "key": key, "value": value}`

### D. Built-in system tool: `update_user_memory`
- Defined as a constant `MEMORY_TOOL` dict at top of `chat_mode.py`
- Always injected into `tools` list alongside skill tools
- System prompt must instruct AI: when user shares personal info/preference, call this tool silently
- Tool_call handler: if `tool_name == "update_user_memory"` → call `PreferenceService.update_memory`, skip skill_executor

### E. Format user_context nicely in system prompt
- If `user_context` is valid JSON, render as `- key: value` bullet list
- If plain text, inject as-is (backward compat)

## Hand-back
Update CHANGELOG.md. Mark this WO complete when all criteria pass.
