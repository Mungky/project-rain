# WO-033: Move Model column to Conversation table
**To:** DB Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Refactor)
**PRD Reference:** §7.2 Backend ↔ DB
**Contracts Touched:** Contract 3 (Postgres)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `db/SYSTEM_PROMPT.md` and `db/INSTRUCTIONS.md`.
2.  Install skills in `db/skills/`.

## Goal
Move the `model` identifier from the `messages` table to the `conversations` table so a model is tied to a session, not individual messages.

## Acceptance Criteria
- [ ] Update `db/schemas/message.py`:
    - Remove the `model` column from the `Message` class.
- [ ] Update `db/schemas/conversation.py`:
    - Add a `model` column (String, nullable=False) to the `Conversation` class.
    - Default value can be "kimi-k2.6:cloud".
- [ ] Generate a new Alembic migration: `alembic revision --autogenerate -m "move_model_to_conversation"`.
- [ ] Apply the migration: `alembic upgrade head`.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
