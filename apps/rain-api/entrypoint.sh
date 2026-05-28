#!/bin/sh
# Production entrypoint: run migrations then start the API server.
#
# The RAIN_FRESH_BOOTSTRAP=1 nuke path was removed after first deploy. It
# turned out to be too dangerous to leave reachable via a Coolify env var
# (one stray '1' = drop schema on next restart). If you ever need to
# bootstrap a fresh DB again, do it explicitly via `alembic stamp head`
# from a manual shell.
set -e

echo "[entrypoint] Running database migrations..."
cd /app/packages/db
uv run --project /app/apps/rain-api alembic upgrade head

echo "[entrypoint] Starting Rain API..."
cd /app/apps/rain-api
exec uv run uvicorn rain_backend.main:app --host 0.0.0.0 --port 8000
