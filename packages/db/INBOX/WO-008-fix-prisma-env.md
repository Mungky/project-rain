# WO-008: Fix Prisma Connection & Env Configuration
**To:** DB Agent
**Phase:** 1 (Critical Fix)
**PRD Reference:** §5.3 (DB Agent), §7.2 (Backend $\leftrightarrow$ DB Contract)
**Contract Reference:** Contract 3 (Postgres)

## Goal
Resolve "No database URL found" error in Prisma Studio and ensure consistent environment configuration.

## Acceptance Criteria
- [ ] **Fix Prisma Environment:**
    - Ensure `db/.env` contains the correct `DATABASE_URL` (e.g., `postgresql://rain:rain@localhost:5432/rain`) that matches the Postgres container in root `docker-compose.yml`.
    - Verify that Prisma Studio can connect to the running Postgres container using this URL.
- [ ] **Env Synchronization:**
    - Standardize the Postgres connection string across `/db` and `/backend` to prevent mismatch.
- [ ] **Prisma Studio Verification:**
    - Run a test attempt of `npx prisma studio` to ensure it opens the visual browser without "No database URL found" errors.

## Hand-back Format
- Verified fix for Prisma connection.
- Updated `.env` and `README.md` with correct connection string instructions.
- `CHANGELOG.md` updated.
