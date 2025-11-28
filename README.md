# Requirements Advisor Client

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

MCP Client web application for requirements management guidance. Connects to a remote MCP Server and provides a chat interface with multi-LLM support.

## Features

- **Multi-LLM Support**: Claude, GPT-4o, and Gemini via LiteLLM
- **MCP Integration**: Connects to remote MCP server using Streamable HTTP transport
- **Topic-Focused**: Strict system prompts ensure responses stay on requirements management topics
- **Chat Interface**: Streamlit-based UI with conversation history
- **Session Persistence**: PostgreSQL/SQLite storage for chat history
- **Docker Support**: Multi-stage builds for development and production
- **Comprehensive Testing**: pytest with async support and coverage

## Architecture

```
┌─────────────────────┐     REST API      ┌─────────────────────┐
│  Streamlit Frontend │ ←───────────────→ │   FastAPI Backend   │
│  (port 8501)        │                   │   (port 8000)       │
│  - Chat UI          │                   │   - MCP Client      │
│  - Session state    │                   │   - LLM Integration │
│  - Custom styling   │                   │   - Session storage │
└─────────────────────┘                   └─────────────────────┘
                                                   │
                                                   ▼
                                         ┌─────────────────────┐
                                         │   MCP Server        │
                                         │   (Railway)         │
                                         │   /mcp endpoint     │
                                         └─────────────────────┘
```

## Project Structure

```
requirements-advisor-client/
├── src/requirements_advisor_client/
│   ├── backend/              # FastAPI application
│   │   ├── main.py           # API endpoints
│   │   ├── config.py         # Pydantic settings
│   │   ├── logging.py        # Loguru setup
│   │   ├── mcp_client.py     # MCP client class
│   │   ├── llm.py            # LiteLLM integration
│   │   ├── models.py         # Pydantic models
│   │   └── database.py       # SQLAlchemy setup
│   └── frontend/             # Streamlit application
│       ├── app.py            # Chat UI
│       ├── config.py         # Frontend settings
│       ├── styles.py         # CSS/branding
│       └── .streamlit/
│           └── config.toml   # Theme configuration
├── tests/                    # pytest test suite
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # Development setup
├── railway.toml              # Railway deployment config
└── pyproject.toml            # Project configuration
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- API keys for at least one LLM provider

### Installation with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/arthurfantaci/requirements-advisor-client.git
cd requirements-advisor-client

# Install dependencies
uv sync

# Install dev dependencies
uv sync --all-extras
```

### Installation with pip

```bash
pip install -e ".[dev]"
```

### Configuration

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required: At least one LLM API key
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...        # Optional
GOOGLE_API_KEY=...           # Optional

# Optional: Override defaults
MCP_SERVER_URL=https://requirements-advisor-production.up.railway.app/mcp
DATABASE_URL=sqlite+aiosqlite:///./data/sessions.db
LOG_LEVEL=INFO
```

### Running Locally

**Option 1: Using uv**

```bash
# Terminal 1: Start backend
uv run uvicorn requirements_advisor_client.backend.main:app --reload --port 8000

# Terminal 2: Start frontend
uv run streamlit run src/requirements_advisor_client/frontend/app.py --server.port 8501
```

**Option 2: Using Docker Compose**

```bash
# Start both services
docker compose up --build

# Or run in detached mode
docker compose up -d --build
```

Open http://localhost:8501 in your browser.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov

# Run specific test file
uv run pytest tests/backend/test_mcp_client.py
```

### Code Quality

```bash
# Run linter
uv run ruff check .

# Run formatter
uv run ruff format .

# Install pre-commit hooks
uv run pre-commit install
```

### Type Checking

The codebase uses type hints throughout. Use your IDE's type checker or run:

```bash
uv run pyright src/
```

## Docker

### Build Images

```bash
# Build backend
docker build --target backend -t advisor-backend .

# Build frontend
docker build --target frontend -t advisor-frontend .
```

### Docker Compose Services

```bash
# Start all services
docker compose up

# Start with PostgreSQL (optional)
docker compose --profile postgres up

# Stop services
docker compose down
```

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVER_URL` | Remote MCP server URL | `https://requirements-advisor-production.up.railway.app/mcp` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./data/sessions.db` |
| `BACKEND_HOST` | Server bind address | `0.0.0.0` |
| `BACKEND_PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_JSON` | Output logs as JSON | `false` |
| `LLM_MAX_ITERATIONS` | Max tool-calling iterations per request | `10` |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GOOGLE_API_KEY` | Google AI API key | - |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `API_URL` | Backend API URL | `http://localhost:8000` |

## Deployment

### Railway

Both services are configured for Railway deployment with the Dockerfile.

1. Create a new Railway project
2. Add Backend service from repository root (target: `backend`)
3. Add Frontend service from repository root (target: `frontend`)
4. Add PostgreSQL database
5. Configure environment variables:
   - Backend: API keys + `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   - Frontend: `API_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:${{backend.PORT}}`

## API Endpoints

### `GET /health`

Health check endpoint.

```json
{
  "status": "healthy",
  "mcp_connected": true,
  "version": "0.1.0"
}
```

### `GET /tools`

List available MCP tools.

### `POST /chat`

Send a chat message.

```json
{
  "message": "How do I write good requirements?",
  "provider": "claude",
  "session_id": null,
  "history": []
}
```

Response:

```json
{
  "response": "Here are some best practices...",
  "session_id": "abc123",
  "tools_used": []
}

### `GET /history/{session_id}`

Get chat history for a session.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install pre-commit hooks (`pre-commit install`)
4. Make your changes
5. Run tests (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

MIT
