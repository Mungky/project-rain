# ROADMAP.md — Project Rain

**Maintained by:** Parent Agent
**Source of truth for:** Phase progress, current sprint, blockers

---

## Phase 1 — Walking Skeleton (Weeks 1–3) — ✅ COMPLETED 2026-04-22

**Goal:** End-to-end chat works with local Ollama, persisted to Postgres, streamed to a Rain-themed UI.

---

## Phase 2 — Memory & Skills (Weeks 4–6) — ✅ COMPLETED 2026-04-23

**Goal:** Documents become queryable RAG context. `skills.sh` works end-to-end. Hosted API providers wired. **UI/UX Polish** (Thinking, Edit, Feedback, Copy).

---

## Phase 3 — Work Mode & Orchestration (Weeks 7–10) — IN PROGRESS

**Goal:** Multi-agent planner with critic loop. Frontend shows agent graph. 4-tier memory.

### Milestone 3.1 — Agent Run Schemas
**Owner:** DB Agent
- [ ] `AgentRun` and `AgentTask` models in `db/schemas`.
- [ ] Enum for task status: `pending`, `running`, `completed`, `failed`.
- [ ] Alembic migration `0005_agent_runs`.

### Milestone 3.2 — Work Mode Orchestrator
**Owner:** Backend Agent
- [ ] `orchestrator/work_mode.py` using Reasoning-Planning-Execution loop.
- [ ] Hierarchical agent roles: `Planner`, `Worker`, `Critic`.
- [ ] JSON schema validation for multi-step plans.

### Milestone 3.3 — WebSocket Streaming
**Owner:** Backend Agent
- [ ] `ws/v1/agent-runs/{run_id}` endpoint.
- [ ] Real-time event push for plan updates and task outputs.

### Milestone 3.4 — Agent Graph UI
**Owner:** Frontend Agent
- [ ] Flow-based visualization (e.g., using `react-flow` or custom canvas).
- [ ] Node status indicators (spinner for running, check for done).
- [ ] Sidebar for inspecting task-specific logs/output.

### Milestone 3.5 — Phase 3 gate
**Owner:** Parent Agent

---

## Phase 4 — Multimodal & Advanced — NOT STARTED

- 4.1 LLaVA integration with VRAM swap-out (Backend)
- 4.2 Stable Diffusion (likely queued/CPU offload)
- 4.3 Deep Research loop
- 4.4 Repo-to-Skill auto-pipeline
- 4.5 (OPTIONAL) Browser Automation provider — only with explicit user consent and warnings

---

## Current Sprint (update weekly)

**Week of:** _<date>_
**In flight:**
- _<milestone>_: _<owner>_, _<status>_
- _<milestone>_: _<owner>_, _<status>_

**Blocked:**
- _<item>_ — _<blocker>_ — _<owner>_

**Next up:**
- _<milestone>_ once _<dependency>_ closes
