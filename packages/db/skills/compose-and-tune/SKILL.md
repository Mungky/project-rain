---
name: compose-and-tune
description: Use this skill when the DB Agent needs to add a service to docker-compose.snippet.yaml or tune an existing one for the 16GB-RAM laptop budget. Triggers when adding Postgres/Qdrant/Redis/MinIO, when memory pressure is reported, or during initial Phase 1 setup. Produces a snippet that Parent Agent merges into root docker-compose.yml.
---

# Skill: compose-and-tune

## Purpose
Define every datastore as a Docker Compose service with: explicit memory caps, healthchecks, persistent volumes, sane defaults for low-RAM hardware, and named anchors so Parent can merge cleanly.

## When to use
- Phase 1: bringing up Postgres + Redis.
- Phase 2: adding Qdrant + MinIO.
- Tuning an existing service after RAM pressure or slow performance.

## When NOT to use
- Backend or frontend service definitions → those are Parent's territory in root compose.
- One-off Docker scripts → use `/db/scripts/`.

## File location
`/db/docker-compose.snippet.yaml` — Parent merges this into root `/docker-compose.yml` via `extends:` or by copying sections.

## Hardware budget (must fit in 16GB RAM, leave room for OS + Ollama)

| Service | mem_limit | Why |
|---|---|---|
| Postgres | 1.5GB | shared_buffers 256MB + work_mem + connections |
| Qdrant | 1.5GB | int8-quantized always_ram + payload indices |
| Redis | 512MB | maxmemory 384MB + overhead |
| MinIO | 512MB | mostly streaming, low resident |
| **Total datastores** | **~4GB** | |
| Ollama (separate, host-mode) | ~3.5GB | LLM in VRAM but RAM-side overhead |
| OS + browser + dev tools | ~6GB | comfortable headroom |
| **Reserve** | **~2.5GB** | |

## Template

```yaml
# /db/docker-compose.snippet.yaml
# This file is the source of truth for all datastore services.
# Parent Agent merges these into root /docker-compose.yml.
#
# Hardware target: 16GB RAM laptop. mem_limit values are tuned accordingly.
# Increase if running on a workstation; do not decrease without testing.

x-restart-policy: &restart unless-stopped

x-healthcheck-defaults: &hc-defaults
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 20s

services:

  postgres:
    image: postgres:16-alpine
    container_name: rain-postgres
    restart: *restart
    environment:
      POSTGRES_DB: rain
      POSTGRES_USER: rain
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-rain}
      # Tuning for 1.5GB container, 16GB host:
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --locale=C"
    command:
      - "postgres"
      - "-c"
      - "shared_buffers=256MB"
      - "-c"
      - "effective_cache_size=768MB"
      - "-c"
      - "work_mem=16MB"
      - "-c"
      - "maintenance_work_mem=64MB"
      - "-c"
      - "max_connections=50"
      - "-c"
      - "wal_buffers=8MB"
      - "-c"
      - "checkpoint_completion_target=0.9"
      - "-c"
      - "random_page_cost=1.1"   # SSD assumption
      - "-c"
      - "log_min_duration_statement=500"  # log slow queries (500ms+)
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"   # localhost-only by default
    mem_limit: 1536m
    mem_reservation: 512m
    healthcheck:
      <<: *hc-defaults
      test: ["CMD-SHELL", "pg_isready -U rain -d rain"]

  redis:
    image: redis:7-alpine
    container_name: rain-redis
    restart: *restart
    command:
      - "redis-server"
      - "--maxmemory"
      - "384mb"
      - "--maxmemory-policy"
      - "allkeys-lru"
      - "--appendonly"
      - "no"
      - "--save"
      - ""                      # disable RDB snapshots (cache-only use)
    ports:
      - "127.0.0.1:6379:6379"
    mem_limit: 512m
    mem_reservation: 128m
    healthcheck:
      <<: *hc-defaults
      test: ["CMD", "redis-cli", "ping"]

  qdrant:                       # Phase 2+
    image: qdrant/qdrant:latest
    container_name: rain-qdrant
    restart: *restart
    environment:
      QDRANT__SERVICE__HTTP_PORT: 6333
      QDRANT__SERVICE__GRPC_PORT: 6334
      QDRANT__STORAGE__OPTIMIZERS__DEFAULT_SEGMENT_NUMBER: 2
      QDRANT__STORAGE__OPTIMIZERS__MAX_OPTIMIZATION_THREADS: 1
      QDRANT__STORAGE__PERFORMANCE__MAX_SEARCH_THREADS: 2
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "127.0.0.1:6333:6333"   # HTTP
      - "127.0.0.1:6334:6334"   # gRPC
    mem_limit: 1536m
    mem_reservation: 512m
    healthcheck:
      <<: *hc-defaults
      test: ["CMD-SHELL", "wget -qO- http://localhost:6333/readyz || exit 1"]

  minio:                        # Phase 2+
    image: minio/minio:latest
    container_name: rain-minio
    restart: *restart
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-rain}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-rainminio}
    volumes:
      - minio_data:/data
    ports:
      - "127.0.0.1:9000:9000"   # API
      - "127.0.0.1:9001:9001"   # Console
    mem_limit: 512m
    mem_reservation: 128m
    healthcheck:
      <<: *hc-defaults
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  minio_data:
```

## Cross-cutting rules

### Bind to 127.0.0.1 only by default
Every port is `"127.0.0.1:NNNN:NNNN"`. Single-user, single-machine. No reason to expose to LAN. Parent can override per env if needed.

### Volumes are named, not bind-mounted
Use named volumes (`postgres_data:`) not host bind mounts. Avoids permission headaches across Mac/Linux/WSL.

### Healthchecks on every service
Backend's `lifespan` waits for healthy state before opening pools. Healthchecks make `docker compose up --wait` actually work.

### `mem_limit` AND `mem_reservation`
- `mem_limit` is the hard cap (OOM-kill above this).
- `mem_reservation` is the soft minimum (Docker keeps it available).
- Together they make scheduling predictable on a constrained machine.

### Pin major versions, allow patch upgrades
- ✓ `postgres:16-alpine` (any 16.x)
- ❌ `postgres:latest` (will break on major version jump)
- ❌ `postgres:16.4.2` (over-pinning, security patches missed)

## Phase rollout

### Phase 1 services
Bring up only `postgres` and `redis`. Comment out qdrant and minio sections (or use compose profiles).

### Phase 2 services
Uncomment `qdrant` and `minio`. After bringing them up, run seeders:
```bash
docker compose up -d
python -m db.seeds.seed_qdrant_collections
python -m db.seeds.seed_minio_buckets
```

## Compose profiles (for selective bring-up)

```yaml
services:
  qdrant:
    profiles: ["phase2", "all"]
    ...
  minio:
    profiles: ["phase2", "all"]
    ...
```

User runs `docker compose --profile phase2 up -d` when ready. Default `docker compose up -d` brings only Phase 1 services.

## Backup & Restore (the unsexy must-have)

`/db/scripts/backup.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d-%H%M%S)
OUT=${1:-./backups/$TS}
mkdir -p "$OUT"

docker exec rain-postgres pg_dump -U rain -Fc rain > "$OUT/postgres.dump"

# Qdrant snapshot (Phase 2+)
if docker ps --format '{{.Names}}' | grep -q rain-qdrant; then
  curl -s -X POST http://localhost:6333/collections/documents/snapshots > "$OUT/qdrant-documents.json"
fi

# Redis: BGSAVE then copy dump.rdb if persistence enabled (it isn't by default)
echo "Backup complete: $OUT"
```

`/db/scripts/restore.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
IN=${1:?path to backup directory}

docker exec -i rain-postgres pg_restore -U rain -d rain --clean < "$IN/postgres.dump"
echo "Restore complete from: $IN"
```

`/db/scripts/reset.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
docker compose down -v   # deletes volumes — irreversible
docker compose up -d --wait
alembic upgrade head
python -m db.seeds.seed_default_user
echo "Reset complete. Clean DB ready."
```

## Quality bar
- Every service has mem_limit, healthcheck, restart policy.
- All ports bound to 127.0.0.1 by default.
- Pinned major version, alpine where available.
- Volumes named, not bind-mounted.
- Snippet validates: `docker compose -f docker-compose.snippet.yaml config` exits 0.
- backup/restore/reset scripts work on a freshly cloned repo.

## Anti-patterns
- ❌ `image: postgres` (no version).
- ❌ `ports: "5432:5432"` (binds 0.0.0.0 — exposed to LAN).
- ❌ No mem_limit (one greedy service can wedge the laptop).
- ❌ Bind-mounting host directories (cross-platform pain).
- ❌ Combining all services into one compose file with no profiles (forces full bring-up).
- ❌ Healthcheck that never fails (e.g., `test: true`).
