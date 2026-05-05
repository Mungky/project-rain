---
name: contract-reviewer
description: Use this skill when reviewing returned work from a subordinate agent (Backend, DB, or Frontend) to verify that their changes conform to CONTRACTS.md. Triggers on completed work orders, pull requests, or when integration tests fail in a way that suggests a contract violation. Produces a pass/fail verdict with specific contract citations. Do NOT use this skill for code style review, performance review, or general feedback.
---

# Skill: contract-reviewer

## Purpose
Verify that work from a subordinate agent honors every contract in `/CONTRACTS.md` that it touches. This is mechanical conformance checking, not taste review.

## When to use
- Closing a work order (mandatory before marking complete).
- Investigating an integration test failure.
- Spot-checking a folder that hasn't been audited recently.

## When NOT to use
- Style or readability concerns → those go to the subordinate as suggestions, not blockers.
- Performance review → separate concern, separate skill.
- Architecture-level decisions → those go to PRD discussion with user.

## Procedure

### Step 1: Identify which contracts apply
List every contract from `/CONTRACTS.md` that the changed code could touch. Examples:
- Touched a route handler → Contract 2 (HTTP API)
- Touched a SQLAlchemy model → Contract 3 (Postgres schema)
- Touched a Qdrant call → Contract 4 (Vector collections)
- Touched anything that reads env vars → Contract 1 (Env vars)

### Step 2: For each applicable contract, run the checks below

#### Contract 1 — Env Vars
- [ ] No new env var introduced without adding it to `/.env.example`.
- [ ] No env var read directly via `os.getenv` in business logic — must go through a settings module.
- [ ] No hardcoded secrets, URLs, or API keys.

#### Contract 2 — Backend ↔ Frontend HTTP
- [ ] OpenAPI schema generates without errors (`curl localhost:8000/openapi.json`).
- [ ] Every new endpoint has a Pydantic request and response model.
- [ ] Streaming endpoints emit the exact envelope: `{"type": "...", "data": ...}`.
- [ ] Error responses use FastAPI's standard `HTTPException` with consistent body shape.
- [ ] No breaking change to an existing endpoint's request/response without a CHANGELOG note flagged "BREAKING".

#### Contract 3 — Backend ↔ Postgres
- [ ] All schema changes have an Alembic migration in `/db/alembic/versions/`.
- [ ] Migration is reversible (downgrade is implemented, not just `pass`).
- [ ] Backend imports models from `db.schemas`, not redefines them.
- [ ] All queries are async (no sync session usage).

#### Contract 4 — Backend ↔ Qdrant
- [ ] Collection name appears in `/db/qdrant_collections.yaml`.
- [ ] Vector size matches the embedding model in use (768 for nomic-embed-text).
- [ ] Payload includes `user_id` for filterability.
- [ ] No collection-per-user pattern (use payload filter).

#### Contract 5 — Backend ↔ Redis
- [ ] Every key starts with `rain:`.
- [ ] Every key has an explicit TTL set (no infinite keys).
- [ ] Key pattern matches one in `/db/REDIS_KEYS.md`. If it's new, REDIS_KEYS.md was updated in the same change.

#### Contract 6 — Skill Manifest (Phase 2+)
- [ ] Manifest validates against `/backend/schemas/skill_manifest.schema.json`.
- [ ] Permissions section is present and minimal (no `network: true` unless justified).
- [ ] Entry point function signature matches `def handle(input: dict) -> dict`.

#### Contract 7 — Provider Adapter
- [ ] New provider implements all four methods: `list_models`, `chat`, `embed`, `health`.
- [ ] `chat` returns an async iterator, not a list.
- [ ] Errors are wrapped in `ChatChunk(type="error", ...)`, not raised through.

#### Contract 8 — WebSocket (Phase 3+)
- [ ] Event names match the documented enum.
- [ ] Every event has a `data` field, even if empty `{}`.

### Step 3: Write the verdict

Output format (post to the work order's reply):

```markdown
# Contract Review — WO-<NNN>

**Verdict:** PASS | FAIL | PASS-WITH-NOTES

## Contracts Applicable
- Contract <N>: <name>
- Contract <N>: <name>

## Findings
### PASS items
- <criterion> ✓

### FAIL items (blocking)
- ❌ <criterion> — <file:line> — <what's wrong> — <how to fix>

### Notes (non-blocking)
- ℹ️ <observation>

## Required Action
<For FAIL: revise and resubmit. For PASS-WITH-NOTES: optional follow-up WO. For PASS: mark complete.>
```

## Quality bar
- A finding without a file:line citation is not actionable. Demand specifics.
- Never say "looks good" — say which contracts pass and which checks within them.
- If a contract isn't in CONTRACTS.md but should be, flag for Parent to add it; don't enforce phantom contracts.

## Anti-patterns
- ❌ Reviewing for style ("rename this variable").
- ❌ Reviewing architecture decisions that the WO didn't open.
- ❌ Failing a WO over a contract the WO wasn't supposed to touch.
- ❌ Letting a "minor" contract violation slide because the feature works. Today's slide is tomorrow's integration test failure.
