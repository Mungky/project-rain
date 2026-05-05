# Project Rain — Product Requirements Document

**Version:** 1.0
**Status:** Source of Truth — All agents MUST read this before making decisions.
**Owner:** Parent Build Orchestrator
**Last Updated:** 2026-04-22

---

## 0. Reading Order for Agents

1. This PRD (full document, end-to-end)
2. Your folder's `INSTRUCTIONS.md`
3. Your folder's `SYSTEM_PROMPT.md`
4. Your folder's `skills/` directory
5. Cross-folder contracts in §7 of this PRD

If anything in your local instructions contradicts this PRD, **the PRD wins**. Raise the conflict to the Parent Agent before proceeding.

---

## 1. Vision

Rain is a **Local AI Operating System** that runs on consumer hardware and reaches output quality competitive with frontier hosted models (Claude Opus, Gemini Ultra) **not by using bigger models, but by using better architecture**: multi-agent orchestration, precision RAG, critic loops, and a plug-and-play skill ecosystem.

**The thesis we are testing:** A 3B-parameter local model, when wrapped in the right orchestration layer, can match a 200B-parameter hosted model on bounded tasks.

---

## 2. Hard Constraints (Non-Negotiable)

| Constraint | Value | Why |
|---|---|---|
| Target dev hardware | RTX 3050 Mobile, 4GB VRAM, 16GB RAM | This is what the user owns. |
| Max single model VRAM footprint | 3.5GB | Leave headroom for OS + embeddings. |
| Default LLM | Ollama with `kimi-k2.6:cloud` | Verified model for current deployment. |
| Embedding model | `nomic-embed-text` (137M, ~300MB) | Runs on CPU, frees GPU for LLM. |
| Backend language | Python 3.11+ with FastAPI | AI ecosystem is Python-native. |
| Frontend framework | Next.js 16 + Tailwind CSS 4 + Zustand + TanStack Query | Per user spec. |
| All data stores | Self-hostable, free tier, no SaaS lock-in | Free-tier mandate. |
| Documentation language | English | Per user spec. |

**No agent may change these values without explicit user approval.**

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 16)                                       │
│  - Chat Mode UI (minimal, fluid)                             │
│  - Work Mode UI (agent graph dashboard)                      │
│  - WebSocket client for streaming                            │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP/REST + WebSocket
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                           │
│  - Provider Adapter Layer (Ollama / API / [Phase 3] Browser) │
│  - Orchestrator (Chat Mode router + Work Mode planner)       │
│  - Skill Executor (sandboxed)                                │
│  - Memory Manager (4-tier)                                   │
└────────┬───────────┬────────────┬───────────────┬────────────┘
         │           │            │               │
         ▼           ▼            ▼               ▼
    ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────────────┐
    │ Qdrant │  │Postgres │  │ Redis  │  │   MinIO      │
    │(vector)│  │(meta)   │  │(state) │  │ (objects)    │
    └────────┘  └─────────┘  └────────┘  └──────────────┘
              ALL IN docker-compose.yml — owned by DB Agent
```

---

## 4. Phased Roadmap (CRITICAL — Build in This Order)

### Phase 1 — Walking Skeleton (Weeks 1–3) ⭐ START HERE
**Goal:** Prove the loop works end-to-end with the smallest possible feature set.

- ✅ DB: `docker-compose.yml` brings up Postgres + Qdrant + Redis (skip MinIO)
- ✅ Backend: FastAPI server, single endpoint `POST /chat`, integrates Ollama only
- ✅ Backend: Provider Adapter interface (even though only Ollama is wired)
- ✅ Backend: Basic conversation persistence to Postgres
- ✅ Frontend: Chat Mode UI only, streaming via Server-Sent Events
- ✅ Frontend: Rain visual identity established (deep blue/slate, glassmorphism)
- ❌ NO Work Mode, NO skills.sh, NO RAG, NO multimodal, NO Browser path

**Phase 1 is "done" when:** User types a message, sees streamed response from local Ollama, conversation persists across page reload.

### Phase 2 — Memory & Skills (Weeks 4–6)
- Qdrant integration: document upload → chunk → embed → store
- RAG retrieval injected into chat context
- MinIO added for raw file storage
- `skills.sh install <github-url>` CLI works for whitelisted skill format
- Skill executor with Docker sandbox
- Hosted API providers added (Anthropic, OpenAI, Google) via adapter
- Frontend: file upload UI, skill management panel

### Phase 3 — Work Mode & Orchestration (Weeks 7–10)
- Work Mode planner: Reasoning → Planning → Execution
- Hierarchical agents: Planner → Worker → Critic
- Agent graph visualization in frontend
- 4-tier memory fully implemented (Short / Episodic / Semantic / Working)
- Self-correction loop (critic feedback → revision)

### Phase 4 — Multimodal & Advanced (Weeks 11+)
- LLaVA / BakLLaVA for image understanding (if VRAM permits — likely needs CPU offload)
- Stable Diffusion integration (likely off-device or queued, given VRAM)
- Deep Research loop
- Repo-to-Skill auto-pipeline
- **Phase 4-Optional:** Browser Automation provider (clearly marked: ToS risk, fragile, user accepts liability)

---

## 5. Component Responsibilities

### 5.1 Parent Agent (root folder `/`)
**Role:** Build Orchestrator — coordinates the build process, NOT a runtime component of Rain.
- Owns this PRD and `ROADMAP.md`, `CONTRACTS.md`, `CHANGELOG.md`
- Reviews work from backend/db/frontend agents at each milestone
- Resolves cross-folder conflicts
- Maintains the integration test suite (E2E tests in `/tests`)
- Owns `docker-compose.yml` at root (composes services from DB Agent's definitions)
- Owns root `README.md` and developer onboarding
- Does NOT write feature code in backend/db/frontend folders

### 5.2 Backend Agent (`/backend`)
**Role:** Builds the FastAPI orchestration server.
- Provider Adapter interface and implementations
- Chat Mode router (Phase 1)
- Work Mode planner (Phase 3)
- Skill executor (Phase 2)
- Memory Manager (Phase 2–3)
- WebSocket / SSE streaming
- Pydantic models for all DTOs (these are the contract surface)
- Pytest suite for backend logic

### 5.3 DB Agent (`/db`)
**Role:** Owns all data layer infrastructure and schemas.
- `docker-compose.yml` snippet for each datastore (Parent composes them)
- PostgreSQL schemas + migrations (Alembic)
- Qdrant collection definitions and seeding scripts
- Redis key-naming conventions document
- MinIO bucket policies (Phase 2)
- Backup/restore scripts
- Performance tuning configs for low-RAM hardware

### 5.4 Frontend Agent (`/frontend`)
**Role:** Builds the Next.js 16 user interface.
- Chat Mode UI (Phase 1)
- Work Mode UI with agent graph (Phase 3)
- Rain visual identity (glassmorphism, deep blue/slate, fluid animations)
- API client layer (typed against backend's OpenAPI schema)
- WebSocket / SSE consumer for streaming
- State management with Zustand
- Server state with TanStack Query
- E2E tests with Playwright

---

## 6. The "Match Opus with a Tiny Model" Strategy

This is the core technical bet of Rain. Every agent must internalize this:

1. **Don't ask the model to do hard things in one shot.** Decompose.
2. **Spend tokens on retrieval, not on the model.** A 3B model with the right 2KB of context beats a 200B model guessing.
3. **Critic loops are cheap.** Run the small model 3 times — once to draft, once to critique, once to revise. Total wall time on RTX 3050 ≈ 8 seconds. Quality jump is enormous.
4. **Cache aggressively.** Redis caches (a) embedding lookups, (b) tool call results, (c) common prompt prefixes.
5. **Templates over freestyle.** Constrain output with JSON schema / grammar (llama.cpp's GBNF, Ollama's `format: json`) wherever possible.
6. **Skill > Prompting.** If a task can be solved by a deterministic skill (regex, API call, calculation), use the skill — don't ask the LLM.

---

## 7. Cross-Folder Contracts

These are the interfaces between agents. **Changing a contract requires Parent Agent approval and a CHANGELOG entry.**

### 7.1 Backend ↔ Frontend
- Communication: HTTP/REST + Server-Sent Events (Phase 1), WebSocket added Phase 3
- Schema source of truth: FastAPI auto-generated OpenAPI at `/openapi.json`
- Frontend MUST regenerate types from this on every backend version bump (use `openapi-typescript`)
- Streaming format: SSE with JSON envelope `{"type": "token"|"tool_call"|"done"|"error", "data": ...}`

### 7.2 Backend ↔ DB
- Postgres: SQLAlchemy 2.x async + Alembic migrations
- Backend imports models from `db/schemas/` (DB Agent publishes Python module)
- Qdrant: backend uses `qdrant-client` against collection names defined in `db/qdrant_collections.yaml`
- Redis: backend follows key conventions in `db/REDIS_KEYS.md`
- Connection strings: ALL via env vars defined in `.env.example` at root (Parent owns this)

### 7.3 Skill Format Contract (Phase 2+)
A skill is a directory with:
```
my-skill/
├── manifest.yaml      # name, version, inputs, outputs, runtime, permissions
├── handler.py         # entry point: def handle(input: dict) -> dict
├── requirements.txt   # pinned deps
└── README.md          # description for LLM to read when deciding to use it
```
- `skills.sh install <github-url>` clones, validates manifest, builds Docker image, registers in Postgres
- Manifest schema is defined in `backend/skill_manifest_schema.json`

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 4GB VRAM cannot fit LLM + embedder simultaneously | HIGH — kills Phase 1 | Embedder runs on CPU (nomic-embed-text is fast on CPU). LLM gets dedicated GPU. |
| Local 3B model output quality too low | HIGH | Critic loop, RAG, structured output, skill offload (per §6). |
| Browser automation provider gets user's accounts banned | MEDIUM | Defer to Phase 4-Optional, require explicit consent dialog, document risks loudly. |
| Skill from GitHub contains malicious code | HIGH | Mandatory Docker sandbox, no host network access by default, permission gateway prompts user before file/network ops. |
| Multimodal + LLM cannot coexist on 4GB | MEDIUM | Dynamic model loading: unload LLM → load LLaVA → process → swap back. Accept latency. |
| Agents working in parallel make conflicting decisions | MEDIUM | Cross-folder contracts in §7, Parent reviews integration points. |

---

## 9. Definition of Done (per Phase)

A phase is "done" only when ALL of these are true:
1. All features in the phase scope work end-to-end on the target hardware (RTX 3050M).
2. Test coverage ≥ 70% on backend, all E2E happy paths pass on frontend.
3. README in each folder documents how to run/test that folder in isolation.
4. Root README's "Quick Start" gets a fresh clone running in < 10 commands.
5. Parent Agent has reviewed and signed off in CHANGELOG.md.

---

## 10. Anti-Goals (Things Rain Will NOT Do in v1)

- Multi-tenant / multi-user. Single user only.
- Mobile apps. Web only.
- Built-in monetization, billing, subscriptions.
- Cluster/distributed deployment. Single-machine only.
- Replacing the OS file manager / browser / shell. Rain is an app, not a literal OS.
- Fine-tuning models on user data. Use RAG instead.

---

## 11. Glossary

- **Adapter** — Provider abstraction so backend doesn't care if model is local/API/browser.
- **Agent (build-time)** — One of the 4 AI assistants writing code (Parent, Backend, DB, Frontend).
- **Agent (runtime)** — A spawned worker in Rain's Work Mode (Planner, Worker, Critic).
- **Skill** — A pluggable, sandboxed capability installable via `skills.sh`.
- **PnP** — Plug-and-Play (refers to GitHub repo → skill pipeline).
- **Tri-DB** — Postgres + Qdrant + Redis (MinIO is a fourth, treated separately).
