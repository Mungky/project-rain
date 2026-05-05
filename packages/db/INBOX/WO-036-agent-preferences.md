# WO-036: Database Foundation for Proper Agent
**To:** DB Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Patenkan)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `db/SYSTEM_PROMPT.md`.
2.  Install all skills in `db/skills/`.

## Goal
Prepare the database to store user-defined agent instructions, preferences, and finalize the model-per-conversation move.

## Acceptance Criteria
- [ ] **Finalize Model Move**: Ensure the `conversations` table has a `model` column and the `messages` table no longer has it (Move logic from WO-033).
- [ ] **User Preferences Table**: Create a new table `user_preferences`:
    - `id`: UUID (Primary Key).
    - `user_id`: UUID (Foreign Key to users).
    - `custom_system_prompt`: Text (To store global instructions like "Always be concise").
    - `user_context`: Text (To store facts about the user like "I prefer Next.js").
    - `api_keys`: JSONB (To store encrypted/raw API keys for hosted providers - placeholder for now).
- [ ] **Migration**: Generate and apply Alembic migration `0003_agent_preferences`.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
