#
# Rain-API — FastAPI Backend
# Build: docker build -t rain-api apps/rain-api
#

FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2 / pycryptodome
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package resolution
ADD https://astral.sh/uv/install.sh /tmp/uv-install.sh
RUN sh /tmp/uv-install.sh && rm /tmp/uv-install.sh
ENV PATH="/root/.local/bin:$PATH"

# Copy workspace package sources (editable deps need real source on disk
# for hatchling metadata validation during `uv sync`)
COPY pyproject.toml uv.lock /app/
COPY packages/db/ /app/packages/db/
COPY packages/rain_brain/ /app/packages/rain_brain/
COPY packages/brain_mcp/ /app/packages/brain_mcp/

# Copy rain-api source (also needed before sync for editable install)
COPY apps/rain-api/ /app/apps/rain-api/

# Install all deps + workspace editable installs
WORKDIR /app/apps/rain-api
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "rain_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
