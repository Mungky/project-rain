# Rain Backend

FastAPI server that orchestrates LLM providers, manages memory, executes skills, and streams responses to the frontend.

## Architecture

- **FastAPI** with async/await throughout
- **Pydantic v2** for request/response validation
- **SQLAlchemy 2.x async** with Postgres
- **Redis** for caching and session state
- **Ollama** as the primary LLM provider (Phase 1)
- **Provider Adapter Pattern** for interchangeable LLM backends

## Structure

```
backend/
├── src/rain_backend/
│   ├── api/
│   │   ├── v1/              # REST endpoints
│   │   │   ├── health.py    # Health check endpoint
│   │   │   └── ...          # Phase 1: conversations.py, messages.py, models.py
│   │   └── deps.py          # FastAPI dependencies
│   ├── providers/
│   │   ├── base.py          # Provider Protocol (Contract 7)
│   │   ├── ollama.py        # Ollama provider implementation
│   │   └── ...              # Phase 2: anthropic.py, openai.py, google.py
│   ├── schemas/
│   │   └── common.py        # Common response schemas
│   ├── memory/              # Phase 2: 4-tier memory system
│   ├── orchestrator/        # Phase 1/3: Chat/Work modes
│   ├── skills/             # Phase 2: Skill executor
│   ├── streaming/          # Phase 1: SSE helpers
│   ├── settings.py         # Environment configuration
│   └── main.py             # FastAPI app factory
├── tests/
│   ├── conftest.py         # Pytest fixtures
│   ├── test_health.py      # Health endpoint tests
│   └── unit/
│       └── test_providers/
│           └── test_ollama.py
├── pyproject.toml          # Dependencies & tooling
├── .env.example            # Environment variables template
└── INSTRUCTIONS.md         # Backend Agent instructions
```

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
# Edit .env to match your setup
```

### 2. Install Dependencies

Using uv:

```bash
uv sync
```

Or pip:

```bash
pip install -e .
pip install -e ".[dev]"  # for development
```

### 3. Start Database Services

Ensure Postgres and Redis are running (reference `db/docker-compose.snippet.yaml`):

```bash
# Start from project root
docker-compose -f db/docker-compose.snippet.yaml up -d
```

### 4. Run the Backend

```bash
uvicorn rain_backend.main:app --reload --port 8000
```

The server will start at `http://localhost:8000`.

## Development

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rain_backend

# Run specific test file
pytest tests/test_health.py
```

### Linting & Formatting

```bash
# Lint
ruff check .

# Format
ruff format .

# Type checking
mypy src
```

## API Endpoints

### Phase 1 (Current)

- `GET /v1/health` - Health check endpoint
- `GET /openapi.json` - OpenAPI schema

### Coming in Phase 1

- `GET /v1/conversations` - List conversations
- `GET /v1/conversations/{id}` - Get conversation with messages
- `POST /v1/conversations` - Create conversation
- `DELETE /v1/conversations/{id}` - Soft delete conversation
- `POST /v1/conversations/{id}/messages` - Send message & stream response

## Testing with curl

```bash
# Health check
curl http://localhost:8000/v1/health

# OpenAPI schema
curl http://localhost:8000/openapi.json | jq .
```

## Notes

- All async I/O, no blocking calls
- Environment variables via `pydantic-settings`
- Type hints everywhere
- `ruff` for linting, `mypy` for type checking
- Test coverage ≥ 70% required