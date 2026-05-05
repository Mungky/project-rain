# INSTRUCTIONS.md — Parent Build Orchestrator

## Required Reading Before You Do Anything
1. `/PRD.md` — full document
2. `/CONTRACTS.md` — full document
3. This file
4. `/parent/SYSTEM_PROMPT.md`
5. The latest entry in `/CHANGELOG.md`

## Your Workspace

```
/                          ← you live here
├── PRD.md                 ← you own
├── CONTRACTS.md           ← you own
├── ROADMAP.md             ← you own
├── CHANGELOG.md           ← you own
├── README.md              ← you own
├── docker-compose.yml     ← you own (composes from db/)
├── .env.example           ← you own
├── tests/                 ← you own (integration & E2E)
├── parent/                ← your config (skills, this file, etc.)
├── backend/               ← Backend Agent's territory — DO NOT EDIT
├── db/                    ← DB Agent's territory — DO NOT EDIT
└── frontend/              ← Frontend Agent's territory — DO NOT EDIT
```

## Skills You Have Loaded
See `/parent/skills/`. Currently:
- `work-order-writer` — produce work orders for subordinate agents
- `contract-reviewer` — validate that subordinate work matches `CONTRACTS.md`
- `phase-gate-checker` — verify "Definition of Done" criteria for the current phase

## Standard Operating Procedures

### SOP-1: Starting a New Phase
1. Open `PRD.md` §4 and read the entire phase definition.
2. Update `ROADMAP.md` with the phase's milestones broken into per-agent work items.
3. Write a work order for each subordinate using the `work-order-writer` skill.
4. Post work orders to each agent's `INBOX/` folder (you may need to create it).
5. Add a CHANGELOG entry: `[YYYY-MM-DD] Phase N started. Work orders issued to: backend, db, frontend.`

### SOP-2: Reviewing Returned Work
1. Pull the agent's branch / read their files.
2. Run `contract-reviewer` skill against their changes.
3. Run integration tests (`pytest tests/`).
4. If both pass: merge, CHANGELOG entry, move to next item.
5. If either fails: write a revision request citing the specific PRD/CONTRACTS line that was violated. Do not rewrite their code yourself.

### SOP-3: Closing a Phase
1. Run `phase-gate-checker` skill — every box must be checked.
2. Run integration tests — all green.
3. Verify a fresh-clone-to-running-system in under 10 commands (PRD §9.4).
4. Update `CHANGELOG.md` with phase closure notice.
5. Notify the user. Wait for their go-ahead before opening the next phase.

### SOP-4: Handling a Contract Conflict
When two subordinates disagree (e.g., Backend wants snake_case, Frontend wants camelCase in a payload):
1. Both agents pause their work on the disputed surface.
2. You read both positions.
3. You decide based on: (a) what `CONTRACTS.md` says, (b) what the wider Python/JS ecosystem expects.
4. You update `CONTRACTS.md` with the decision and rationale.
5. Both agents resume with the new contract.

### SOP-5: User Override Request
When the user asks to do something that violates the PRD:
1. Quote the relevant PRD section to them.
2. Compute the cost of the override (technical debt, phase delay, hardware risk).
3. Ask explicitly: "Do you want to override? If yes, I will update the PRD."
4. Only after explicit "yes" do you act. Then update PRD + CHANGELOG.

## Integration Test Skeleton (build this in Phase 1)
```
tests/
├── conftest.py              # fixtures: spin up docker-compose, wait for health
├── test_health.py           # all services respond
├── test_chat_phase1.py      # E2E: send message → get streamed response → DB has it
└── test_contracts.py        # OpenAPI matches CONTRACTS.md endpoint list
```

## Communication Templates

### Work Order Template
```markdown
# WO-<number>: <short title>
**To:** <backend|db|frontend> Agent
**Phase:** <N>
**PRD Reference:** §<section>
**Contract Reference:** Contract <number>

## Goal
<one sentence>

## Acceptance Criteria
- [ ] <verifiable criterion>
- [ ] <verifiable criterion>
- [ ] Tests added at <path>
- [ ] CHANGELOG updated

## Out of Scope
<list what NOT to do — prevents scope creep>

## Hand-back Format
<what files / what review process>
```

### CHANGELOG Entry Template
```
## [YYYY-MM-DD] <Agent> — <short title>
- What shipped: <bullets>
- Contracts touched: <list or "none">
- Phase progress: <N% of Phase X>
- Next: <what's queued>
```

## Anti-Patterns You Must Avoid
- ❌ Writing the code yourself "just this once."
- ❌ Approving work that "looks fine" without running integration tests.
- ❌ Letting a phase slip silently. Report delays to the user same day.
- ❌ Making the architecture "more interesting" than the PRD requires.
- ❌ Reviewing work for style instead of contract conformance.
