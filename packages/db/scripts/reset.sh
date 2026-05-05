#!/usr/bin/env bash
# /db/scripts/reset.sh
set -euo pipefail

echo "Resetting database environments..."

# 1. Tear down existing containers and volumes
docker compose down -v

# 2. Bring up Phase 1 services and wait for healthchecks
docker compose up -d --wait

# 3. Apply all migrations from base to head
alembic upgrade head

# 4. Seed default environment
python -m db.seeds.seed_default_user

echo "Reset complete. Clean DB ready."
