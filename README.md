# 🌧️ Rain — Local AI Operating System

> A multi-agent AI OS that runs on your own hardware and competes with frontier hosted models — not by being bigger, but by being smarter about orchestration.

**Status:** Phase 1 (Walking Skeleton) — in progress.
**Hardware target:** RTX 3050 Mobile / 4GB VRAM / 16GB RAM (designed up from this baseline).

---

## What is Rain?

Rain is a local-first AI assistant with two operating modes:

- **Chat Mode** — fast, intuitive assistant for daily tasks (Phase 1).
- **Work Mode** — multi-agent orchestrator for complex tasks: Reasoning → Planning → Execution with critic loops (Phase 3).

Powered by:
- **Local models** via Ollama (default), with optional bring-your-own API keys for hosted providers.
- **Plug-and-play skills** installable from GitHub via `skills.sh`.
- **Precision RAG** over your own documents.
- **Self-evolving memory** that learns from every interaction.

The thesis: a 3B-parameter local model, properly orchestrated, beats a 200B-parameter hosted model on bounded tasks.

---

## Repository Layout

```
/                    ← Parent: PRD, contracts, roadmap, integration tests
├── backend/         ← FastAPI orchestration server
├── db/              ← Postgres / Qdrant / Redis / MinIO definitions & schemas
├── frontend/        ← Next.js 16 app
└── tests/           ← Cross-folder E2E
```

Each folder has its own `README.md`, `INSTRUCTIONS.md`, `SYSTEM_PROMPT.md`, and `skills/` directory — these are how the building agents know what to do.

---

## Quick Start (target: ≤ 10 commands)

> Requires: Docker, Node.js 20+, Python 3.11+, pnpm, Ollama running locally.

```bash
# 1. Clone
git clone <repo-url> rain && cd rain

# 2. Copy env defaults
cp .env.example .env

# 3. Bring up datastores
docker compose up -d --wait

# 4. Apply schemas + seed
cd db && alembic upgrade head && python -m seeds.seed_default_user && cd ..

# 5. Pull a tiny model (one-time)
ollama pull kimi-k2.6:cloud
ollama pull nomic-embed-text

# 6. Start backend
cd backend && uv sync && uv run uvicorn rain_backend.main:app --reload &

# 7. Start frontend
cd frontend && pnpm install && pnpm dev
```

Open `http://localhost:3000` and start chatting.

---

## Key Documents

- **[PRD.md](./PRD.md)** — Source of truth. Read this first.
- **[CONTRACTS.md](./CONTRACTS.md)** — How the four folders talk to each other.
- **[ROADMAP.md](./ROADMAP.md)** — Phased milestones.
- **[CHANGELOG.md](./CHANGELOG.md)** — Chronological record.

---

## Built by Four Agents

Rain is being constructed by four AI agents working in parallel:

| Agent | Folder | Owns |
|---|---|---|
| **Parent** | `/` | Coordination, contracts, integration tests |
| **Backend** | `/backend` | FastAPI, providers, orchestrator, skills executor |
| **DB** | `/db` | Postgres, Qdrant, Redis, MinIO, schemas, migrations |
| **Frontend** | `/frontend` | Next.js app, chat UI, agent graph (Phase 3) |

Each agent has a SYSTEM_PROMPT, INSTRUCTIONS, and skill bundle in its folder. The Parent agent issues work orders, reviews returned work against contracts, and gates phase transitions.

---

## License

TBD.
