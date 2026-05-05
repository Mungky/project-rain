# WO-017: Set up Qdrant and MinIO Datastores
**To:** DB Agent
**From:** Parent Agent
**Date:** 2026-04-22
**Priority:** high
**Phase:** 2
**PRD Reference:** §4 Phase 2, Milestone 2.1, 2.2
**Contracts Touched:** Contract 4 (Backend ↔ Qdrant), Contract 1 (Env Vars)

## Goal
Add Qdrant and MinIO to the `docker-compose.yml` and initialize their configurations.

## Context
Phase 2 requires vector storage (Qdrant) for RAG and object storage (MinIO) for raw documents and skill artifacts. We are transitioning from the Phase 1 "Skeleton" to a full "Memory & Skills" setup.

## Acceptance Criteria
- [ ] Add `qdrant` service to `docker-compose.yml` with port 6333 exposed.
- [ ] Add `minio` service to `docker-compose.yml` with ports 9000 (API) and 9001 (Console) exposed.
- [ ] Update `/.env.example` with default Qdrant and MinIO connection strings and credentials.
- [ ] Create `db/qdrant_collections.yaml` defining the `documents` collection (vector_size: 768, distance: Cosine).
- [ ] Create a seed script `db/seeds/seed_minio_buckets.py` that creates `rain-uploads` and `rain-skill-artifacts` buckets.
- [ ] Both services pass health checks in docker-compose.
- [ ] CHANGELOG.md entry appended.

## Out of Scope
- Backend implementation of upload API.
- Document processing logic.

## Dependencies
- Blocked by: none
- Blocks: WO-018 (Document tables)

## Hand-back
Standard.
