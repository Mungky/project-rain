# WO-025: Implement Document List and Delete API
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2
**PRD Reference:** §4 Phase 2, Milestone 2.4 (Cleanup)
**Contracts Touched:** Contract 2 (Backend ↔ Frontend HTTP), Contract 4 (Backend ↔ Qdrant)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
Before starting this Work Order, you MUST:
1.  Read your `backend/SYSTEM_PROMPT.md`.
2.  Read your `backend/INSTRUCTIONS.md`.
3.  Install all skills in `backend/skills/`.

## Goal
Implement the ability to list all uploaded documents and delete them (cleaning up Postgres, MinIO, and Qdrant).

## Context
We have the upload pipeline (WO-019), but users currently have no way to see what they've uploaded or remove old documents. This is a prerequisite for the Document Management UI.

## Acceptance Criteria
- [ ] **List Endpoint**:
    - Add `GET /v1/documents` in `api/v1/documents.py`.
    - Return a list of `DocumentResponse` objects.
    - Support pagination (limit/offset or cursor).
- [ ] **Delete Endpoint**:
    - Add `DELETE /v1/documents/{document_id}` in `api/v1/documents.py`.
    - Implement a `delete_document` method in `DocumentService`.
    - **Postgres**: Delete the row (or soft delete, but for RAG cleanup hard delete is preferred if user requests).
    - **MinIO**: Delete the raw file from the `rain-uploads` bucket.
    - **Qdrant**: Delete all points associated with the `document_id` using a filter.
- [ ] **Integrity**: Ensure the deletion is atomic across all three stores (if one fails, handle it gracefully or log it).
- [ ] Update `DocumentResponse` Pydantic model if necessary.
- [ ] Unit tests for listing and the multi-store deletion logic.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
