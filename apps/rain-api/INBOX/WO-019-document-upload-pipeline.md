# WO-019: Implement Document Upload Pipeline
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-22
**Priority:** high
**Phase:** 2
**PRD Reference:** §4 Phase 2, Milestone 2.4
**Contracts Touched:** Contract 2 (Backend ↔ Frontend HTTP), Contract 4 (Backend ↔ Qdrant)

## Goal
Implement the `POST /v1/documents` endpoint to handle multipart uploads, storage in MinIO, and chunking/embedding for Qdrant.

## Context
This is the core of our RAG (Retrieval Augmented Generation) capability. Documents must be processed in the background (or efficiently in-line for Phase 2 start) to make them searchable.

## Acceptance Criteria
- [ ] Implement `POST /v1/documents` using FastAPI's `UploadFile`.
- [ ] Integrate with MinIO (via `boto3` or `aioboto3`) to store raw files in `rain-uploads`.
- [ ] Implement a `document_service.py` to handle chunking (target ~512 tokens).
- [ ] Implement embedding using Ollama's `nomic-embed-text` model (ensure it runs on CPU as per PRD §2).
- [ ] Store chunks and vectors in Qdrant `documents` collection with `user_id` and `document_id` metadata.
- [ ] Update document status in Postgres to `ready` upon completion.
- [ ] Unit tests for chunking logic and service layer (mocking MinIO/Qdrant).
- [ ] CHANGELOG.md entry appended.

## Out of Scope
- Frontend UI for uploads (WO-020).
- Retrieval logic in chat (WO-021).

## Dependencies
- Blocked by: WO-018 (Document schemas)
- Blocks: WO-020 (Frontend upload UI)

## Hand-back
Standard.
