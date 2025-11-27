# Multi-stage Dockerfile for Requirements Advisor Client
# Supports both backend and frontend targets

# =============================================================================
# Stage 1: Builder - Install dependencies with UV
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache .

# Install Guardrails hub validators for input/output filtering
RUN . /app/.venv/bin/activate && \
    guardrails hub install hub://tryolabs/restricttotopic --no-install-local-models --quiet && \
    guardrails hub install hub://guardrails/toxic_language --quiet && \
    guardrails hub install hub://guardrails/detect_pii --quiet

# =============================================================================
# Stage 2: Backend runtime
# =============================================================================
FROM python:3.11-slim-bookworm AS backend

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY --chown=appuser:appuser src/ /app/src/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "requirements_advisor_client.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage 3: Frontend runtime
# =============================================================================
FROM python:3.11-slim-bookworm AS frontend

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY --chown=appuser:appuser src/ /app/src/

# Copy streamlit config
COPY --chown=appuser:appuser src/requirements_advisor_client/frontend/.streamlit /app/.streamlit

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8501

# Start command
CMD ["streamlit", "run", "src/requirements_advisor_client/frontend/app.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.fileWatcherType", "none", \
     "--browser.gatherUsageStats", "false"]
