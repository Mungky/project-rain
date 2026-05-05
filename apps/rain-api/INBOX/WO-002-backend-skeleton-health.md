# WO-002: Backend Skeleton & Health Check
**To:** Backend Agent
**Phase:** 1
**PRD Reference:** §4 (Phase 1), §5.2
**Contract Reference:** Contract 2 (HTTP), Contract 3 (Postgres), Contract 5 (Redis), Contract 7 (Provider Adapter)

## Goal
Implement the FastAPI server skeleton, the Provider Adapter interface, and the first functional health check endpoint.

## Acceptance Criteria
- [ ] `pyproject.toml` and `settings.py` configured with environment variable loading (per `.env.example`).
- [ ] FastAPI app factory implemented in `main.py` with a lifespan handler for Redis & Postgres connection pools.
- [ ] `Provider` Protocol implemented in `providers/base.py` exactly as defined in Contract 7.
- [ ] `OllamaProvider` implementation created with full test coverage for `list_models` and `chat` (simulated/real).
- [ ] `GET /v1/health` endpoint implemented:
    - Returns `{status, ollama, postgres, redis}`.
    - Uses `asyncio.gather` with a 2s timeout for each check.
- [ ] OpenAPI schema generates correctly and matches Contract 2.
- [ ] Pytest suite for the basic server logic implemented and passing.

## Out of Scope
- Conversation CRUD (Deferred to WO-003).
- SSE Streaming implementation (Deferred to WO-004).
- Other LLM providers (Deferred to Phase 2).

## Hand-back Format
- All files committed to `/backend`.
- Updated `CHANGELOG.md` with a detailed entry.
- Verified `GET /v1/health` responds correctly with the current environment state.
