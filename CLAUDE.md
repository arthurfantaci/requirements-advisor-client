# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

MCP Client web application that connects to a remote MCP Server for requirements management guidance. Features a FastAPI backend with multi-LLM support (Claude, GPT-4, Gemini via LiteLLM) and a Streamlit frontend with Jama-inspired branding.

## Architecture

```
requirements-advisor-client/
├── src/requirements_advisor_client/
│   ├── __init__.py
│   ├── backend/                    # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, endpoints, lifespan
│   │   ├── config.py               # Pydantic settings from .env
│   │   ├── logging.py              # Loguru setup
│   │   ├── mcp_client.py           # MCP client class
│   │   ├── llm.py                  # LiteLLM integration
│   │   ├── models.py               # Pydantic request/response models
│   │   └── database.py             # SQLAlchemy async models
│   └── frontend/                   # Streamlit application
│       ├── __init__.py
│       ├── app.py                  # Chat UI
│       ├── config.py               # Frontend settings
│       └── styles.py               # CSS/branding
├── tests/                          # pytest test suite
│   ├── conftest.py                 # Shared fixtures
│   ├── backend/
│   │   ├── test_config.py
│   │   ├── test_mcp_client.py
│   │   ├── test_llm.py
│   │   ├── test_database.py
│   │   └── test_main.py
│   └── frontend/
│       └── test_app.py
├── Dockerfile                      # Multi-stage build
├── docker-compose.yml              # Dev environment
├── pyproject.toml                  # Project config (uv, ruff, pytest)
├── .env.example                    # Environment template
└── .pre-commit-config.yaml         # Code quality hooks
```

## Development Commands

### Setup

```bash
# Install dependencies with uv
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Backend

```bash
# Run locally with hot reload
uv run uvicorn requirements_advisor_client.backend.main:app --reload --port 8000

# Or use the CLI entry point
uv run requirements-advisor-backend

# Environment variables (set in .env or export):
# - ANTHROPIC_API_KEY (for Claude)
# - OPENAI_API_KEY (for GPT-4)
# - GOOGLE_API_KEY (for Gemini)
# - MCP_SERVER_URL (defaults to production Railway URL)
# - DATABASE_URL (defaults to SQLite for local dev)
# - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR)
```

### Frontend

```bash
# Run locally
uv run streamlit run src/requirements_advisor_client/frontend/app.py --server.port 8501

# Environment variables:
# - API_URL (defaults to http://localhost:8000)
```

### Docker

```bash
# Start all services
docker compose up --build

# Start with PostgreSQL
docker compose --profile postgres up

# Build specific target
docker build --target backend -t advisor-backend .
docker build --target frontend -t advisor-frontend .
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/backend/test_mcp_client.py -v

# Run tests matching pattern
uv run pytest -k "test_health"
```

### Code Quality

```bash
# Lint and auto-fix
uv run ruff check . --fix

# Format code
uv run ruff format .

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

## Key Components

### Backend

- **config.py**: Pydantic settings with .env support
- **logging.py**: Loguru with human-readable or JSON output
- **mcp_client.py**: Async MCP client with Streamable HTTP transport
- **llm.py**: LiteLLM wrapper for unified tool calling across providers
- **models.py**: API request/response Pydantic models
- **database.py**: SQLAlchemy async with PostgreSQL/SQLite support
- **main.py**: FastAPI app with `/health`, `/tools`, `/chat`, `/history` endpoints

### Frontend

- **config.py**: Frontend settings (API_URL)
- **styles.py**: Jama branding CSS (orange #E86826)
- **app.py**: Streamlit chat interface with session state

## MCP Server Connection

The client connects to: `https://requirements-advisor-production.up.railway.app/mcp`

Using Streamable HTTP transport (not SSE).

## Coding Standards

- **Python**: 3.11+
- **Type hints**: Required on all functions
- **Docstrings**: Google style with Args/Returns
- **Line length**: 100 characters
- **Linting**: Ruff with rules E, W, F, I, B, C4, UP, SIM
- **Testing**: pytest-asyncio for async tests
- **Logging**: Use loguru, not print()

## Railway Deployment

Both services deploy via Railway using the Dockerfile:

- Backend: Target `backend`, healthcheck at `/health`
- Frontend: Target `frontend`

Environment variables for Railway:
- Backend: API keys, `DATABASE_URL=${{Postgres.DATABASE_URL}}`
- Frontend: `API_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:${{backend.PORT}}`
