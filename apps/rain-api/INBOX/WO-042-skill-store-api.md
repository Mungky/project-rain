# WO-042: Implement Skill Installation and Uninstallation API
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Patenkan - App Store)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1. Read `backend/SYSTEM_PROMPT.md`.
2. Install all skills in `backend/skills/`.

## Goal
Implement endpoints to install skills via Git URL and uninstall them directly from the UI.

## Context
We want to move away from CLI-based skill management. The backend should handle cloning, manifest validation, and database registration.

## Acceptance Criteria
- [ ] **Install Endpoint**:
    - Add `POST /v1/skills/install` in `api/v1/skills.py`.
    - Body should accept a `git_url` string.
    - **Logic**: 
        1. Clone the repo to a temporary directory.
        2. Validate the `manifest.yaml`.
        3. Move it to `skills_registry/`.
        4. Trigger `SkillService.sync_registry()` to register in DB.
- [ ] **Uninstall Endpoint**:
    - Add `DELETE /v1/skills/{skill_name}`.
    - **Logic**:
        1. Delete the folder from `skills_registry/`.
        2. Remove/Disable the record in the database.
- [ ] **Dependency**: Ensure `git` is available in the environment or use a python library like `GitPython`.
- [ ] Unit tests for the installation flow (mocking the git clone).
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
