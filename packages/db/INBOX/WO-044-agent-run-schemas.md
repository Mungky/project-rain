# WO-044: Schemas for Multi-Agent Orchestration (Work Mode)
**To:** DB Agent
**From:** Parent Agent
**Date:** 2026-04-24
**Priority:** high
**Phase:** 3 (Work Mode)
**PRD Reference:** §4 Phase 3, Milestone 3.1
**Contracts Touched:** Contract 3 (Postgres)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1. Read `db/SYSTEM_PROMPT.md` and `db/INSTRUCTIONS.md`.
2. Install all skills in `db/skills/`.

## Goal
Implement the database schema to track complex multi-step agent plans and individual task executions.

## Context
Phase 3 introduces "Work Mode". Unlike Chat Mode, Work Mode breaks a request into multiple tasks (Planning -> Execution -> Critique). We need to store these runs and their results.

## Acceptance Criteria
- [ ] **AgentRun Table**:
    - `id`: UUID (Primary Key)
    - `conversation_id`: UUID (Foreign Key)
    - `goal`: Text (The user's original request)
    - `plan_json`: JSONB (The generated plan with multiple steps)
    - `status`: Enum (pending, running, completed, failed)
    - `started_at`: TIMESTAMPTZ
    - `finished_at`: TIMESTAMPTZ (nullable)
- [ ] **AgentTask Table**:
    - `id`: UUID (Primary Key)
    - `run_id`: UUID (Foreign Key to AgentRun)
    - `parent_task_id`: UUID (Self-reference for sub-tasks, nullable)
    - `role`: String (planner, worker, critic)
    - `input`: JSONB
    - `output`: JSONB (nullable)
    - `status`: Enum (pending, running, completed, failed)
    - `error`: Text (nullable)
- [ ] **Migration**: Generate and apply Alembic migration `0005_agent_runs`.
- [ ] Update `db/schemas/__init__.py` to export new models.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
