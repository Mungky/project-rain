# WO-022: Update Messages Schema for UI/UX Features
**To:** DB Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (UI/UX Polish)
**PRD Reference:** §4 Phase 2, Milestone 2.10
**Contracts Touched:** Contract 3 (Postgres)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
Before starting this Work Order, you MUST:
1.  Read your `db/SYSTEM_PROMPT.md` to assume your identity as the DB Agent.
2.  Read your `db/INSTRUCTIONS.md` for your specific operational procedures.
3.  Install all skills located in the `db/skills/` directory (e.g., `alembic-migration-author`, `schema-modeller`, etc.) to use your specialized tools.

## Goal
Update the `messages` table to support user feedback (thumbs up/down) and store reasoning/thinking content.

## Context
As part of the UI/UX polish, we need to persist feedback ratings and the internal reasoning process of the model or RAG retrieval for audit and display purposes.

## Acceptance Criteria
- [ ] Update `db/schemas/message.py` to add two new columns to the `Message` class:
    - `feedback`: Integer (nullable). Convention: `1` for Thumbs Up, `-1` for Thumbs Down, `NULL` for none.
    - `reasoning_content`: Text (nullable). To store content inside `<think>` tags or RAG context summaries.
- [ ] Generate a new Alembic migration: `alembic revision --autogenerate -m "add_feedback_and_reasoning_to_messages"`.
- [ ] Ensure the migration uses `TIMESTAMPTZ` (via the established `Base` configuration).
- [ ] Apply the migration to the development database: `alembic upgrade head`.
- [ ] Verify the table structure using `psql` or a similar tool.
- [ ] Update `CHANGELOG.md` with the new schema changes.

## Hand-back
Standard completion report (`.completed.md`).
