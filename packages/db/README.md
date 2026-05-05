# DB Agent - Database Management

This folder contains the source of truth for all persistent data in Project Rain.

## Quick Start

### 1. Bring up Datastores

**Phase 1 (Postgres + Redis only):**
```bash
docker compose -f docker-compose.snippet.yaml up -d --wait
```

**Phase 2+ (all services including Qdrant + MinIO):**
```bash
docker compose --profile phase2 -f docker-compose.snippet.yaml up -d --wait
```

### 2. Run Migrations & Seed
```bash
alembic upgrade head
python -m db.seeds.seed_default_user
```

For Phase 2, also seed MinIO buckets:
```bash
pip install minio
python db/seeds/seed_minio_buckets.py
```

### 3. Full Reset
```bash
./scripts/reset.sh
```

## Services

| Service | Port | Profile | Purpose |
|---|---|---|---|
| Postgres 16 | 5432 | default | Relational data |
| Redis 7 | 6379 | default | Cache + session state |
| Qdrant | 6333/6334 | phase2 | Vector storage (RAG) |
| MinIO | 9000/9001 | phase2 | Object storage (documents, artifacts) |

## Maintenance
- **Reset Database:** `./scripts/reset.sh` (Warning: wipes all data)
- **Backup Data:** `./scripts/backup.sh`
- **Restore Data:** `./scripts/restore.sh`

## Notes
- All application logic uses SQLAlchemy + Alembic. Prisma Studio is admin-only visualization.
- Ports bound to 127.0.0.1 (localhost only).