# backend2 — auth / sessions / RAG chat (FastAPI)
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# system deps for psycopg2 / healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY openapi.yaml ./openapi.yaml
COPY README.md ./README.md

EXPOSE 8002

# Compose overrides DATABASE_URL / REDIS_URL / BACKEND1_BASE_URL / OPENAI_* / JWT_SECRET
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
