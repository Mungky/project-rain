#!/bin/sh
# Production entrypoint: run migrations then start the API server.
set -e

echo "[entrypoint] Running database migrations..."
cd /app/packages/db
uv run --project /app/apps/rain-api alembic upgrade head

echo "[entrypoint] Starting Rain API..."
cd /app/apps/rain-api
exec uv run uvicorn rain_backend.main:app --host 0.0.0.0 --port 8000
