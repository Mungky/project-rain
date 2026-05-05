# WO-005: Visual DB Access (Prisma Studio)
**To:** DB Agent
**Phase:** 1 (Interlude)
**PRD Reference:** §9.4 (Quick Start / Onboarding)
**Contract Reference:** Contract 3 (Postgres)

## Goal
Provide a non-technical visual interface for the user to inspect the database content without writing SQL.

## Acceptance Criteria
- [ ] Integrate Prisma into the `/db` folder solely as an administration and visualization tool.
- [ ] Create a `schema.prisma` file that maps to the existing SQLAlchemy models (`User`, `Conversation`, `Message`).
- [ ] Provide a clear a short-guide/instruction in `db/README.md` on how the user can run `npx prisma studio` to open the visual browser.
- [ ] Ensure Prisma Studio connects correctly to the Postgres container defined in `docker-compose.snippet.yaml`.
- [ ] Verify that the user can view, filter, and edit records in the `User`, `Conversation`, and `Message` tables via the UI.

## Out of Scope
- Using Prisma for actual application logic (Backend must continue using SQLAlchemy).
- Complex database migrations via Prisma (Stick to Alembic).

## Hand-back Format
- All necessary Prisma config files committed to `/db`.
- Updated `CHANGELOG.md` with a detailed entry.
- Detailed "How-to-Open" instructions for the non-programmer user.
