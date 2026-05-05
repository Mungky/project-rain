# WO-039: Session-Specific Skill Configuration
**To:** DB Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Patenkan - Skills Control)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `db/SYSTEM_PROMPT.md`.
2.  Install all skills in `db/skills/`.

## Goal
Update the database to support session-specific skill settings and user prompt references.

## Acceptance Criteria
- [ ] **Update Conversations Table**:
    - Add `auto_skills`: Boolean, default=true (If true, AI chooses skills automatically).
    - Add `enabled_skills`: JSONB, default=[] (List of skill names/IDs enabled manually when auto_skills is false).
- [ ] **Update User Preferences**:
    - Ensure the table from WO-036 exists and can store `custom_system_prompt` (This will be the "Reference" in the UI).
- [ ] **Migration**: Generate and apply Alembic migration `0004_session_skills_config`.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
