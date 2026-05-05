# WO-001: Datastores & Initial Schema
**To:** DB Agent
**Phase:** 1
**PRD Reference:** §4 (Phase 1), §5.3
**Contract Reference:** Contract 3 (Postgres), Contract 5 (Redis)

## Goal
Establish the foundational data layer (Postgres & Redis) and initial schemas to unblock Backend development.

## Acceptance Criteria
- [ ] `db/docker-compose.snippet.yaml` created with Postgres and Redis services.
- [ ] Containers configured with resource limits (tuned for 16GB RAM) and healthchecks.
- [ ] `db/scripts/reset.sh` implemented to wipe and restart datastores from clean state.
- [ ] `schemas/base.py` created with standard naming conventions and SQLAlchemy 2.x async mixins.
- [ ] `User`, `Conversation`, and `Message` entities implemented per PRD/Contract 3.
- [ ] Alembic migration `0001_initial` generated; upgrade/downgrade cycle verified.
- [ ] `seeds/seed_default_user.py` created for deterministic environment setup.
- [ ] `db/tests/test_migrations.py` passes.

## Out of Scope
- Qdrant and MinIO integration (Deferred to Phase 2).
- Advanced query optimization.
- Multi-user authentication logic.

## Hand-back Format
- All files committed to `/db`.
- Updated `CHANGELOG.md` with a detailed entry.
- Verified success of `reset.sh` and alembic upgrade.
