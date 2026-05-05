# WO-009: CRITICAL FIX - Prisma Studio Connectivity
**To:** DB Agent
**Phase:** 1 (Critical Fix / Final Attempt)
**PRD Reference:** §9.4 (Onboarding)
**Contract Reference:** Contract 3 (Postgres)

## Goal
Completely resolve the "No database URL found" error in Prisma Studio. This is a blocking issue for the user's visual verification.

## Acceptance Criteria
- [ ] **Strict File Placement:** 
    - Ensure `.env` is located EXACTLY in `D:\006 Restard\Rain\project-rain-build\db\.env`.
    - Ensure `schema.prisma` is located exactly where the tool expects it (ideally in `D:\006 Restard\Rain\project-rain-build\db\prisma\schema.prisma`).
- [ ] **Exact URL Formatting:** 
    - The `.env` file MUST contain: `DATABASE_URL="postgresql://rain:rain@localhost:5432/rain"`
    - The `schema.prisma` MUST contain: `url = env("DATABASE_URL")`
- [ ] **Manual Verification (Mandatory):**
    - The agent MUST run `npx prisma studio` locally (or via a test container) and verify that the application starts without errors.
- [ ] **Instructions Update:**
    - Update `db/README.md` to provide the EXACT command to run if they need to pass the URL manually as a fallback: `npx prisma studio --url "postgresql://rain:rain@localhost:5432/rain"`.

## Hand-back Format
- Proof of verification (Log output showing Prisma Studio successfully started).
- Updated `CHANGELOG.md` with a "CRITICAL FIX" label.
- Verified that the user can open the UI without any further configuration.

## Warning
This is a repeat failure. Do not report "Fixed" until you have personally verified that the command `npx prisma studio` works from the `/db` directory.
