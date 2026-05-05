# Changelog — DB Agent

All notable changes to the database layer are documented here.
Each entry references the Work Order (WO) and Contract sections affected.

## [Phase 2] — 2026-04-23

### WO-036 & WO-039: Session Skills Config and User Preferences
- Created `schemas/user_preferences.py` — UserPreference model (`user_id`, `custom_system_prompt`, `user_context`, `api_keys`).
- Updated `schemas/conversation.py` to add `auto_skills` (Boolean, default=true) and `enabled_skills` (JSONB, default=[]).
- Updated `schemas/user.py` to add `preference` relationship to `UserPreference`.
- Updated `prisma/schema.prisma` to include `UserPreference` model and `Conversation` additions for sync.
- Generated Alembic migration `b1d26d39f399` (`session_skills_config`) — adds `user_preferences` table and columns to `conversations`.
- Migration tested and applied cleanly.

**Contracts affected:** Contract 3 (Postgres)
**Backend impact:** Backend can now persist user-level preferences (prompts/context) and per-conversation skill enablement configurations.

### WO-033: Refactor Model identifier to Conversation
- Moved `model` column from `messages` to `conversations` table.
- Updated `schemas/message.py` and `schemas/conversation.py` models.
- Implemented data backfill: `conversations.model` is populated from the latest associated message if available, otherwise defaults to "kimi-k2.6:cloud".
- Enforced project naming conventions and added missing comments for all existing tables (`users`, `conversations`, `messages`, `documents`, `skills`, `skill_executions`).
- Generated Alembic migration `3d8803d16ffc` — fully reversible with data restoration in downgrade.
- Migration tested: upgrade → downgrade → upgrade cycle clean.

**Contracts affected:** Contract 3 (Postgres)
**Backend impact:** **BREAKING.** `Message.model` has been removed. Backend must now read/write `Conversation.model`. Backend import path `db.schemas.Conversation` now includes the `model` attribute.

### WO-022: Update Messages Schema for UI/UX Features
- Added `feedback` column to `messages` — Integer, nullable (1 = thumbs up, -1 = thumbs down, NULL = none)
- Added `reasoning_content` column to `messages` — Text, nullable (model thinking/RAG context)
- Generated Alembic migration `3c737a5a064e` — reversible, downgrade drops both columns
- Migration tested: upgrade → downgrade → upgrade cycle clean

**Contracts affected:** Contract 3 (Postgres)
**Backend impact:** `Message.feedback` and `Message.reasoning_content` are nullable — existing rows unaffected. Backend can start writing these fields immediately.

---

## [Phase 2] — 2026-04-22

### WO-018: Create Document and Skill schemas
- Created `schemas/document.py` — Document model (id, user_id FK CASCADE, filename, mime, minio_key, qdrant_collection, status enum: uploading/processing/ready/error, timestamps)
- Created `schemas/skill.py` — Skill model (id, name, version, manifest_json JSONB, docker_image, installed_at, enabled) + SkillExecution model (id, skill_id FK RESTRICT, conversation_id FK SET NULL, input, output, duration_ms, error, timestamps)
- Added `document_status` Postgres enum type (uploading, processing, ready, error)
- Generated Alembic migration `3c737a5a064d` — adds documents, skills, skill_executions tables with all FKs, indices, comments
- Updated `schemas/__init__.py` to export Document, Skill, SkillExecution
- Added back-populates: User.documents, Conversation.skill_executions
- Migration tested: upgrade → downgrade → upgrade cycle clean

**Contracts affected:** Contract 3 (Postgres Phase 2 tables)
**Backend impact:** New models importable from `db.schemas`: `Document`, `Skill`, `SkillExecution`. Import path stable. SkillExecution.conversation_id uses SET NULL (preserves audit trail on conversation delete). SkillExecutions → Skills uses RESTRICT (prevent skill deletion if executions exist).

---

### WO-017: Set up Qdrant and MinIO Datastores
- Added `qdrant` service to `docker-compose.snippet.yaml` (profiles: phase2, all; ports 6333/6334; mem_limit 1536m; healthcheck on /readyz)
- Added `minio` service to `docker-compose.snippet.yaml` (profiles: phase2, all; ports 9000/9001; mem_limit 512m; healthcheck on /minio/health/live)
- Created `db/qdrant_collections.yaml` defining `documents` collection (vector_size: 768, distance: Cosine, int8 scalar quantization, on_disk: true)
- Created `db/seeds/seed_minio_buckets.py` — idempotent seeder for `rain-uploads` and `rain-skill-artifacts` buckets
- Updated `backend/.env.example` with default MinIO credentials (MINIO_ACCESS_KEY=rain, MINIO_SECRET_KEY=rainminio)

**Contracts affected:** Contract 4 (Qdrant), Contract 1 (env vars)
**Backend impact:** New env vars QDRANT_URL, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY now have defaults. Backend can start using Qdrant client and MinIO client.

---

## [Phase 1] — 2026-04-22

### WO-001: Datastores & Initial Schema
- Created `docker-compose.snippet.yaml` with Postgres 16 + Redis 7, healthchecks, memory limits
- Created `schemas/base.py` with DeclarativeBase, naming conventions, TimestampMixin, SoftDeleteMixin, UUIDPKMixin
- Created `schemas/user.py` — User model (id, username, email, timestamps)
- Created `schemas/conversation.py` — Conversation model (id, user_id FK, title, soft-delete, timestamps)
- Created `schemas/message.py` — Message model (id, conversation_id FK, role enum, content, model, tokens, timestamps)
- Created `alembic/versions/0001_initial.py` — reversible migration for users, conversations, messages
- Created `seeds/seed_default_user.py` — deterministic UUID seed for rain_admin
- Created `tests/test_migrations.py` — upgrade/downgrade/upgrade cycle test
- Created `scripts/reset.sh` — tear down + bring up + migrate + seed

**Contracts affected:** Contract 3 (Postgres), Contract 5 (Redis)