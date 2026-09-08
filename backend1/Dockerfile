# backend1 — ingest + retrieval (FastAPI)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# system deps for psycopg2 / crypto
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

RUN uv sync --frozen --no-dev

EXPOSE 8001

# Compose overrides DATABASE_URL / QDRANT_URL / OLLAMA_BASE_URL / JWT_SECRET
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
