# WO-018: Create Document and Skill schemas
**To:** DB Agent
**From:** Parent Agent
**Date:** 2026-04-22
**Priority:** high
**Phase:** 2
**PRD Reference:** §4 Phase 2, Milestone 2.3
**Contracts Touched:** Contract 3 (Backend ↔ Postgres)

## Goal
Implement SQLAlchemy models and Alembic migrations for Document and Skill management.

## Context
We need to track uploaded documents (metadata, storage keys) and installed skills in the relational database to link them to users and conversations.

## Acceptance Criteria
- [ ] Create `db/schemas/document.py` with `Document` entity (id, user_id, filename, mime, minio_key, qdrant_collection, status).
- [ ] Create `db/schemas/skill.py` with `Skill` and `SkillExecution` entities.
- [ ] Implement `status` enum for Documents (uploading, processing, ready, error).
- [ ] Generate Alembic migration `0002_documents_and_skills`.
- [ ] Migration must be reversible (downgrade implemented).
- [ ] Update `db/schemas/__init__.py` to export new models.
- [ ] CHANGELOG.md entry appended.

## Out of Scope
- Integration with MinIO/Qdrant in Python code (Backend Agent responsibility).

## Dependencies
- Blocked by: WO-017 (Infrastructure setup)
- Blocks: WO-019 (Document upload pipeline)

## Hand-back
Standard.
