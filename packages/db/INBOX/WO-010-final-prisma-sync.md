# WO-010: FINAL ULTIMATUM - Prisma Tooling Synchronization
**To:** DB Agent
**Phase:** 1 (Critical Infrastructure)
**PRD Reference:** §9.4 (Onboarding)
**Contract Reference:** Contract 3 (Postgres)

## Goal
Ensure Prisma Studio correctly displays existing database tables created by SQLAlchemy and operates without manual URL flags.

## Acceptance Criteria
- [ ] **Automatic Env Detection:**
    - Resolve the `.env` detection failure. The user MUST be able to run `npx prisma studio` without providing a `--url` argument.
    - Verify the exact location of `.env` relative to `package.json` or `schema.prisma`.
- [ ] **Schema Synchronization (The "Empty Table" Fix):**
    - Run `npx prisma db pull`. This is mandatory to synchronize the `schema.prisma` file with the actual tables currently in Postgres.
    - Verify that `User`, `Conversation`, and `Message` models are now physically present in the `schema.prisma` file.
- [ ] **Stream Error Resolution:**
    - Investigate and fix the `ERR_STREAM_UNABLE_TO_PIPE` error. If it's a version mismatch, provide a specific `package.json` with locked Prisma versions.
- [ ] **End-to-End Manual Test:**
    - Run `npx prisma studio` $\to$ Open Browser $\to$ Click on `Conversation` table $\to$ Confirm that it is NOT empty (since seed_default_user was run).

## Hand-back Format
- Log output showing the results of `npx prisma db pull`.
- Updated `CHANGELOG.md` with a "FINAL FIX" label.
- A "Guaranteed to Work" one-liner command for the user to launch the UI.

## Warning
If this fails again, I will strip Prisma from the project and replace it with a simpler, zero-config visual tool. This is the last attempt to make Prisma work as planned.
