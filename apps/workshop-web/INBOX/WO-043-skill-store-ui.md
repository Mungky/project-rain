# WO-043: Build Skill Store and Knowledge Base Settings
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Patenkan - App Store)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1. Read `frontend/SYSTEM_PROMPT.md`.
2. Install all skills in `frontend/skills/`.

## Goal
Transform the placeholders in SettingsModal into a functional Skill Store and Knowledge Base manager.

## Acceptance Criteria
- [ ] **Skill Store (Tab Skills)**:
    - Replace the hardcoded list with a real list of installed skills (Fetch from `GET /v1/skills`).
    - Add an input field for "Git URL" and an "Install" button.
    - Show a loading spinner during installation.
    - Connect the "Discard" button to the `DELETE /v1/skills/{name}` API.
- [ ] **Neural Archive (Tab KB)**:
    - Integrate the document upload logic (from WO-026) here.
    - Show a list of uploaded documents with a delete option.
- [ ] **API Credentials (Tab API)**:
    - Ensure the API key fields correctly save to the `user_preferences` API (from WO-040).
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
