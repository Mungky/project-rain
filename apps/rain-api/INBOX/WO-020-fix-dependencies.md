# WO-020: Fix missing dependencies for document uploads
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-22
**Priority:** blocker
**Phase:** 2
**PRD Reference:** §4 Phase 2
**Contracts Touched:** none

## Goal
Add `python-multipart` to the backend dependencies to enable file uploads.

## Context
During verification of WO-019, it was discovered that `python-multipart` is missing, which causes `POST /v1/documents` to fail when receiving `UploadFile`.

## Acceptance Criteria
- [ ] Add `python-multipart` to `dependencies` in `backend/pyproject.toml`.
- [ ] Run `uv sync` to update `uv.lock`.
- [ ] Verify that the backend starts without errors.

## Hand-back
Standard.
