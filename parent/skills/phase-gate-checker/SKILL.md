---
name: phase-gate-checker
description: Use this skill when the Parent Agent believes a phase is ready to close, or when the user asks "are we done with Phase N?". Verifies every Definition-of-Done criterion from PRD §9 against actual project state. Produces a go/no-go verdict with a punch list of remaining items. Do NOT use this skill mid-phase for progress checks — that's CHANGELOG's job.
---

# Skill: phase-gate-checker

## Purpose
Mechanical verification that every Definition-of-Done criterion from PRD §9 holds before declaring a phase complete and unlocking the next phase.

## When to use
- Subordinate agents have delivered all WOs for the phase.
- User asks "can we move to Phase N+1?"
- Mid-phase health check requested by user.

## When NOT to use
- Daily progress tracking → CHANGELOG.
- Reviewing a single WO → contract-reviewer skill.
- Deciding what to build next within a phase → ROADMAP.md.

## Procedure

For each Definition-of-Done item in PRD §9, run the corresponding check below and mark ✓ or ❌.

### DoD-1: All features in phase scope work end-to-end on RTX 3050M
- [ ] List every feature from PRD §4 for this phase.
- [ ] For each, identify the integration test in `/tests/` that proves it.
- [ ] Run the full integration test suite. All in-phase tests pass.
- [ ] If no test exists for a phase feature: ❌ FAIL — write the missing test.
- [ ] Bonus: if user has run on actual RTX 3050M hardware, note that in verdict.

### DoD-2: Test coverage ≥ 70% on backend, all E2E happy paths pass
- [ ] Run `pytest --cov=backend tests/` — coverage report ≥ 70%.
- [ ] Run Playwright suite in `/frontend/e2e/` — all green.
- [ ] If frontend has no E2E for a Phase 1 happy path (send message → see response): ❌.

### DoD-3: README in each folder documents how to run/test in isolation
- [ ] `/backend/README.md` exists, has "Run locally", "Run tests", "Common errors" sections.
- [ ] `/db/README.md` exists, has "Bring up", "Apply migrations", "Reset" sections.
- [ ] `/frontend/README.md` exists, has "Dev server", "Build", "E2E tests" sections.
- [ ] Each README's commands actually work on a fresh clone (verify by walking through them).

### DoD-4: Root README's Quick Start gets a fresh clone running in < 10 commands
- [ ] Count commands in `/README.md` "Quick Start". Must be ≤ 10.
- [ ] Walk through them on a fresh `git clone` to a temp dir. System reaches usable state.
- [ ] If any command requires manual intervention not documented (e.g., "now edit this file"): ❌.

### DoD-5: Parent has reviewed and signed off in CHANGELOG.md
- [ ] CHANGELOG has an entry of the form `## [YYYY-MM-DD] Parent — Phase N closed`.
- [ ] That entry summarizes what shipped vs. what was planned.
- [ ] Any descoped items are explicitly listed with rationale.

## Output format

```markdown
# Phase <N> Gate Check — <YYYY-MM-DD>

**Verdict:** GO | NO-GO

## Scoreboard
| DoD | Status | Notes |
|-----|--------|-------|
| 1: Features E2E on hardware | ✓ / ❌ | <detail> |
| 2: Coverage & E2E green | ✓ / ❌ | <coverage %, failing tests> |
| 3: Folder READMEs | ✓ / ❌ | <missing files> |
| 4: Quick Start ≤ 10 cmds | ✓ / ❌ | <actual count, failures> |
| 5: CHANGELOG signoff | ✓ / ❌ | <missing entry?> |

## Punch List (if NO-GO)
1. <action item with owner>
2. <action item with owner>

## If GO
- [ ] Tag the repo `phase-<N>-complete`.
- [ ] Append CHANGELOG closure entry.
- [ ] Notify user with one-paragraph summary.
- [ ] Open Phase N+1 by issuing the first work orders (use work-order-writer skill).
```

## Quality bar
- NO-GO with a single ❌ is correct behavior. Phases don't close on partial completion.
- If a DoD criterion is genuinely impossible in this phase (e.g., user lacks the hardware to verify), document it as a deferred check, do NOT silently mark it ✓.
- Do not invent additional DoD criteria. If you think a check is missing, propose a PRD update; don't enforce it ad hoc.

## Anti-patterns
- ❌ Marking ✓ because "it should work" without running the check.
- ❌ Letting a phase close with an open contract violation discovered by contract-reviewer.
- ❌ Closing Phase N while Phase N+1 features have already crept in (those need their own gate).
