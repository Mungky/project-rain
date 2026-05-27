#!/bin/sh
# Production entrypoint.
#
# Modes:
#   RAIN_FRESH_BOOTSTRAP=1  → drop all tables, recreate from SQLAlchemy models,
#                             stamp alembic at head. For first prod deploy or
#                             after migration drift. Unset after success.
#   (default)               → run `alembic upgrade head`.
set -e

if [ "${RAIN_FRESH_BOOTSTRAP:-0}" = "1" ]; then
    echo "[entrypoint] RAIN_FRESH_BOOTSTRAP=1 — nuking schema and recreating from models."
    cd /app/apps/rain-api
    uv run python <<'PYEOF'
import asyncio
import os
import sys

sys.path.insert(0, "/app/packages")

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

import db.schemas  # noqa: F401 — populate Base.metadata with all tables
from db.schemas.base import Base


async def main() -> None:
    dsn = os.environ["POSTGRES_DSN"]
    engine = create_async_engine(dsn)
    async with engine.begin() as conn:
        # Drop public schema to clean alembic_version + any leftover types
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO rain"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("[bootstrap] Schema recreated from SQLAlchemy models.")


asyncio.run(main())
PYEOF

    cd /app/packages/db
    echo "[entrypoint] Stamping alembic at head..."
    uv run --project /app/apps/rain-api alembic stamp head
else
    echo "[entrypoint] Running database migrations..."
    cd /app/packages/db
    uv run --project /app/apps/rain-api alembic upgrade head
fi

echo "[entrypoint] Starting Rain API..."
cd /app/apps/rain-api
exec uv run uvicorn rain_backend.main:app --host 0.0.0.0 --port 8000
