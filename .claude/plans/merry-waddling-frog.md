# Project Rain — 5-Phase Implementation Plan

## Context

Project Rain is an AI-driven software design platform. The Workshop (Phase 3) has comprehensive design docs (`workshop_design/` v0.1.0) but implementation is ~40% complete. Agent pipelines are mocked with `asyncio.sleep`, the Workshop AssistantPanel uses `setTimeout` for fake responses, and drag-drop on the ReactFlow canvas is broken. This plan progressively fixes, unifies, and builds out the system per the existing ADR decisions.

---

## Phase 1: Fix & Stabilize

**Goal:** Every interaction produces real backend results. No more mock data.

### Tasks

1. **Fix Canvas drag-drop** — Move `onDragOver`/`onDrop` from wrapper `<div>` to `<ReactFlow>` component props. ReactFlow's internal pane consumes events; using its own props is the supported pattern.
   - Files: `CanvasTab.tsx`

2. **Wire AssistantPanel to real SSE** — Replace `setTimeout` mock with `sseStream()` call to `POST /v1/workshop/projects/{id}/chat-action`. Backend streams ChatChunk events (token, tool_call, done, error).
   - Files: `AssistantPanel.tsx`, `routes.py`, `orchestrator.py`

3. **Replace work_mode.py mocks** — Replace `asyncio.sleep(2)` in `_run_planner` and `asyncio.sleep(3)` in `_run_execution_loop` with real LLM provider calls using the ReAct pattern from `chat_mode.py`.
   - Files: `work_mode.py`, `prompt_templates.py`

4. **Fix context-extractor mock** — Replace `setTimeout` simulation in `context-extractor-store.ts` with real API call to backend context extraction.
   - Files: `context-extractor-store.ts`, new extraction endpoint

5. **Wire PreviewTab to Docker sandbox** — Replace WebContainer with backend sandbox: `POST .../codegen` → `POST .../sandbox/start` → iframe proxy.
   - Files: `PreviewTab.tsx`, `routes.py`

**Expected output:** Real streaming in AssistantPanel. Working drag-drop. Real context extraction. Docker-based preview.

---

## Phase 2: Agent Pipeline (Survey → Codegen → Review)

**Goal:** Full multi-agent pipeline executes when user sends a Workshop command.

### Tasks

1. **Implement full pipeline in orchestrator.py** — `run_survey()` → `run_codegen()` → `run_review()` → commit to Ground Truth with optimistic locking. Follow contracts in `04_AGENT_WORKFLOW.md`.
   - Files: `orchestrator.py`, new prompt templates in `workshop/prompts/`

2. **SSE streaming for pipeline progress** — `chat-action` endpoint returns `StreamingResponse` yielding events: task_started, token, task_completed, ground_truth_updated, run_completed.
   - Files: `routes.py`, `orchestrator.py`

3. **Create AgentRun/AgentTask records** — Track every pipeline run in existing `agent_runs`/`agent_tasks` tables with proper status transitions.
   - Files: `orchestrator.py`

4. **Canvas auto-update on agent output** — When SSE streams `ground_truth_updated`, canvas nodes/edges update automatically.
   - Files: `AssistantPanel.tsx`, `workshop-store.ts`, `CanvasTab.tsx`

5. **Architect Advisor button** — Manual trigger for architecture consultation (Sonnet 4.6, does NOT write to Ground Truth).
   - Files: `AssistantPanel.tsx`, `orchestrator.py`, `routes.py`

**Expected output:** Type "Tambah tombol diskon" → see streaming pipeline (Survey analyzing → Codegen generating → Review validating) → canvas updates with new nodes.

---

## Phase 3: Neural Systems (Context + Archive + Baseline)

**Goal:** Brain subsystems fully operational and driving agent quality.

### Tasks

1. **Neural Context — auto-summarization** — Fire `_extract_context_background` after Workshop pipeline runs. Surface entries in Workshop UI context panel.
   - Files: `orchestrator.py`, `context-store.ts`, new `ContextPanel.tsx`

2. **Neural Archive — from attachments/files** — Archive generated code files to Qdrant documents collection tagged with project_id. Enable RAG over generated code.
   - Files: `routes.py`, `document_service.py`, `codegen/engine.py`

3. **Neural Baseline — layered YAML config** — Structured preference system: Global → Project → Persona layers. YAML editor in frontend. Extends existing `PreferenceService`.
   - Files: `preference_service.py`, new migration, new `BaselineEditor.tsx`

4. **Persona tuning schema** — Add `tuning_config` JSONB to `model_capability_overrides`. Read-only for now, ready for Phase 5+.
   - Files: new migration, settings UI

**Expected output:** Context panel with extracted knowledge. Archivable files. YAML baseline editor. Tuning-ready schema.

---

## Phase 4: Storm Dashboard (Orchestrator UI)

**Goal:** Storm becomes a dashboard-style command center, distinct from Drizzle's chat interface.

### Tasks

1. **Storm dashboard UI** — Replace chat interface with: project status overview, active agent run timeline, quick-action buttons (Analyze, Add Feature, Review All, Bootstrap), run history with re-run.
   - Files: `AssistantPanel.tsx`, new `StormDashboard.tsx`

2. **Project bootstrap flow** — "Bikin aplikasi kasir" → Survey (bootstrap mode, confidence ≥0.7) → preview proposed nodes → Codegen generates all → Review → canvas populated.
   - Files: `orchestrator.py`, `workshop-store.ts`, `StormDashboard.tsx`, `routes.py`

3. **Cost tracking & budget enforcement** — Redis-based spend tracking. Tiered enforcement: $10 badge, $15 warning + prefer local, $19 block Anthropic. Cost meter in header.
   - Files: new `budget_guard.py`, `orchestrator.py`, `StormDashboard.tsx`

4. **WebSocket for agent run monitoring** — Live timeline of agent tasks via WebSocket (reuses existing `manager.broadcast()`).
   - Files: `StormDashboard.tsx`, new `useAgentRunWebSocket.ts`

5. **Model routing decision tree** — Implement `pick_model()` from ADR spec: local for low complexity, Sonnet for medium/high, Opus only on escalation.
   - Files: `model_router.py`, `orchestrator.py`

**Expected output:** Dashboard shows project health, active runs, cost meter. "Bootstrap from description" creates full project. Drizzle chat still works for conversation.

---

## Phase 5: Polish & Export

**Goal:** Success criteria met — non-technical user builds, previews, and exports working app.

### Tasks

1. **Export ZIP with Indonesian README** — Full project + workshop.json + anchors.json + generated README (3-step instructions for awam).
   - Files: `export.py`

2. **Import ZIP** — Parse workshop.json, create project, regenerate anchors.
   - Files: `export.py`

3. **Basic bi-directional sync** — File watcher in sandbox. Last-write-wins + conflict notification (full 3-way merge deferred).
   - Files: new `sync_mediator.py`

4. **3 starter templates** — "Aplikasi Kasir", "Form Survey", "Landing Page". Template selector on landing page.
   - Files: `templates_starter.py`, `workshop/page.tsx`

5. **Error handling & graceful degradation** — All error paths from `04_AGENT_WORKFLOW.md` §4. Error boundaries. Friendly Bahasa Indonesia messages.
   - Files: `orchestrator.py`, `routes.py`, `workshop/[projectId]/page.tsx`

6. **UI polish** — Loading skeletons, animations, diagnostics tab (dev mode), mobile warning.
   - Files: various frontend components

**Expected output:** Non-technical user: template → canvas → preview → export ZIP → `npm run dev` works. All under 10 minutes.

---

## Verification

After each phase, verify:
- **Typecheck:** `bun run --cwd apps/workshop-web typecheck` passes
- **Backend:** `uv run uvicorn rain_backend.main:app` starts without import errors
- **End-to-end:** Open Workshop, create project, type command, see agent respond
- **Infrastructure:** `docker compose -f docker-compose.dev.yml up -d` all services healthy

---

## Key Files Reference

| File | Phases |
|------|--------|
| `apps/rain-api/src/rain_backend/workshop/orchestrator.py` | 1-5 |
| `apps/rain-api/src/rain_backend/workshop/routes.py` | 1-5 |
| `apps/workshop-web/src/components/workshop/AssistantPanel.tsx` | 1,2,4 |
| `apps/workshop-web/src/components/workshop/CanvasTab.tsx` | 1,2 |
| `apps/workshop-web/src/components/workshop/PreviewTab.tsx` | 1,5 |
| `packages/rain_brain/orchestrator/work_mode.py` | 1,2 |
| `packages/rain_brain/services/context_service.py` | 3 |
| `packages/rain_brain/services/preference_service.py` | 3 |
| `packages/rain_brain/orchestrator/model_router.py` | 4 |
| `apps/workshop-web/src/stores/workshop-store.ts` | 1,2,4 |
