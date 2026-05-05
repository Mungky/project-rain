---
name: work-order-writer
description: Use this skill when the Parent Agent needs to issue a unit of work to a subordinate agent (Backend, DB, or Frontend). Triggers when starting a phase, breaking down a milestone, requesting a revision, or assigning a cross-cutting task. Produces a complete work order with acceptance criteria, contract references, and out-of-scope guards. Do NOT use this skill for status updates, reviews, or user-facing communication.
---

# Skill: work-order-writer

## When to use
Any time you (Parent Agent) need to assign discrete work to Backend, DB, or Frontend Agent. Symptoms: "I need to ask backend to add an endpoint," "DB needs to migrate a table," "Frontend has to wire up the new contract."

## When NOT to use
- General status updates → just write to CHANGELOG.md
- Reviewing returned work → use `contract-reviewer` skill
- Talking to the user → speak plainly, no template
- Tasks that touch your own root files → just do them

## Required structure

A work order is a markdown file written to `/<target-agent>/INBOX/WO-<NNN>-<slug>.md`. Filename uses three-digit zero-padded ID and kebab-case slug.

```markdown
# WO-001: <imperative title>
**To:** <backend|db|frontend> Agent
**From:** Parent Agent
**Date:** <YYYY-MM-DD>
**Priority:** <blocker|high|normal|low>
**Phase:** <1|2|3|4>
**PRD Reference:** §<section.subsection>
**Contracts Touched:** <list contract numbers from CONTRACTS.md, or "none">

## Goal
<Exactly one sentence stating what done looks like.>

## Context
<2–5 sentences. Why now? What upstream/downstream depends on this?>

## Acceptance Criteria
Every item must be objectively verifiable. No "make it good" language.
- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] Unit tests added at <path>, coverage ≥ 70% on new code
- [ ] Contract conformance verified (run `contract-reviewer`)
- [ ] CHANGELOG.md entry appended

## Out of Scope (Do Not Touch)
<List explicit non-goals. This is the scope-creep firewall.>
- <thing not to do>
- <other agent's territory>

## Dependencies
- Blocked by: <other WO numbers, or "none">
- Blocks: <other WO numbers, or "none">

## Hand-back
When done, the agent:
1. Updates `CHANGELOG.md` using the standard template.
2. Writes `/<target-agent>/INBOX/WO-<NNN>.completed.md` with a 1-paragraph summary.
3. Tags Parent Agent for review.
```

## Quality bar (self-check before issuing)
1. **Title is imperative.** "Add health endpoint" not "Health endpoint discussion."
2. **Goal is testable.** A reviewer can say yes/no without ambiguity.
3. **At least one acceptance criterion mentions tests.**
4. **Out-of-Scope section is non-empty** — every WO has scope it could creep into; name it.
5. **PRD reference is specific** — `§4` not `§Phase 1`.
6. **No two WOs depend circularly on each other.** Check dependencies graph.

## Anti-patterns
- ❌ "Implement the auth system" — too big, decompose into 3-5 WOs.
- ❌ "Make it work like the user wants" — Parent translates user wishes into spec, not the subordinate.
- ❌ Issuing a WO that touches a contract before updating CONTRACTS.md.
- ❌ Bundling multiple unrelated changes — one WO, one outcome.

## Example (good)

```markdown
# WO-007: Implement /v1/health endpoint
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-25
**Priority:** blocker
**Phase:** 1
**PRD Reference:** §3 (Architecture Overview), §4 Phase 1
**Contracts Touched:** Contract 2 (Backend ↔ Frontend HTTP)

## Goal
Expose `GET /v1/health` returning JSON with reachability of Ollama, Postgres, and Redis.

## Context
Frontend Agent needs this endpoint to render the system status indicator in the chat header. DB Agent has confirmed Postgres and Redis containers are up. WO-006 (Ollama provider scaffolding) just landed.

## Acceptance Criteria
- [ ] `GET /v1/health` returns 200 with body `{"status": "ok", "ollama": bool, "postgres": bool, "redis": bool}`
- [ ] Returns 503 if any required service is down (Postgres or Redis); Ollama down → status "degraded" not failure
- [ ] Each check has 2s timeout, parallel via asyncio.gather
- [ ] Unit test: mock all three providers, assert response shapes for all 8 combinations
- [ ] OpenAPI schema generated correctly (`GET /openapi.json` includes the endpoint)
- [ ] CHANGELOG entry added

## Out of Scope
- Authentication (Phase 2)
- MinIO check (not in Phase 1)
- Caching health results (premature)

## Dependencies
- Blocked by: WO-006 (Ollama provider scaffold)
- Blocks: WO-012 (Frontend status indicator)

## Hand-back
Standard.
```
