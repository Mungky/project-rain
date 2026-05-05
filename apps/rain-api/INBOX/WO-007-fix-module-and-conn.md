# WO-007: Fix Module Resolution & DB Connectivity
**To:** Backend Agent
**Phase:** 1 (Critical Fix)
**PRD Reference:** §5.2 (Backend), §7.2 (Backend $\leftrightarrow$ DB Contract)
**Contract Reference:** Contract 3 (Postgres)

## Goal
Resolve `ModuleNotFoundError: No module named 'db'` and ensure stable connectivity to Postgres database.

## Acceptance Criteria
- [ ] **Fix Python Path:**
    - Ensure the Backend can resolve the `/db` folder as a package. 
    - Implementation: Do NOT use relative path hacks. Either update `pyproject.toml` to include the `/db` path or implement a clean mechanism to add the workspace root to `sys.path` in `main.py`.
    - Verify that `from db.schemas import ...` works across all services.
- [ ] **Fix Env Configuration:**
    - Sync `.env` with `POSTGRES_DSN` matching the root `docker-compose.yml` (`postgresql+asyncpg://rain:rain@localhost:5432/rain`).
- [ ] **Connection Handshake:**
    - Implement a startup check in the FastAPI lifespan handler that attempts a simple `SELECT 1` query to Postgres.
    - If the handshake fails, the server must log a clear "DATABASE CONNECTION FAILURE" error and exit.

## Hand-back Format
- Verified fix for `ModuleNotFoundError`.
- Updated `.env.example` and relevant config files.
- `CHANGELOG.md` updated with the fix.
