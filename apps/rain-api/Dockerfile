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

# Copy workspace packages (editable deps need the monorepo layout)
COPY apps/rain-api/pyproject.toml /app/apps/rain-api/
COPY packages/db/pyproject.toml /app/packages/db/
COPY packages/rain_brain/pyproject.toml /app/packages/rain_brain/
COPY packages/brain_mcp/pyproject.toml /app/packages/brain_mcp/
COPY pyproject.toml uv.lock /app/

# Copy package source for editable installs
COPY packages/db/ /app/packages/db/
COPY packages/rain_brain/ /app/packages/rain_brain/
COPY packages/brain_mcp/ /app/packages/brain_mcp/

# Install deps from the rain-api context
WORKDIR /app/apps/rain-api
RUN uv sync --no-dev -v

# Copy application source
COPY apps/rain-api/src/ /app/apps/rain-api/src/

WORKDIR /app/apps/rain-api
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "rain_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
