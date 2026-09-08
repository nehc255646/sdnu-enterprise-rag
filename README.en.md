# Shandong Normal University Knowledge Base (RAG)

Multi-tenant Q&A over an SDNU knowledge base (`tenant_id` / `X-Tenant-Id`). Demo tenant: `sdnu-demo`.

## Layout

| Path | Role | Default port |
|------|------|--------------|
| `backend1/` | Ingest + vector retrieval (FastAPI + LangChain + Qdrant) | `:8001` |
| `backend2/` | Auth / sessions / chat SSE (FastAPI + LangChain LCEL) | `:8002` |
| `frontend/` | Document management + chat UI (React / Vite / Ant Design) | `:5173` |

## Stack

- FastAPI + LangChain
- SQLAlchemy (Postgres; local SQLite also supported)
- Redis (cache / queue / rate limit)
- Qdrant collection: `sdnu_chunks`
- Secrets via environment variables (see each service `.env.example`)

## Docker Compose (demo)

Run Ollama on the host first, with at least:

- `qwen3-embedding:0.6b`
- `qwen2.5:1.5b`

```bash
cp .env.example .env   # set JWT_SECRET
docker compose up -d --build
```

Then:

- Frontend: http://127.0.0.1:5173
- backend1 OpenAPI: http://127.0.0.1:8001/docs
- backend2 OpenAPI: http://127.0.0.1:8002/docs

After the first start, ingest `knowledge/sdnu/` (login as a demo user with `X-Tenant-Id: sdnu-demo`, or use the scripts in each service README). Without ingest, the document list is empty and chat has nothing to retrieve.

Ollama is not part of Compose; containers reach the host at `host.docker.internal:11434`.

Per-service Compose notes: `backend1/COMPOSE.md`, `backend2/COMPOSE.md`, `frontend/COMPOSE.md`.

### Nested / restricted Docker hosts

On nested Docker or locked-down bridges, the default `overlay2` storage driver or iptables FORWARD rules may break inter-container DNS/TCP. If services hang on DB connect, try `storage-driver: vfs` in `/etc/docker/daemon.json`, ensure containers can reach each other, and keep Ollama listening on `0.0.0.0:11434` (not only `127.0.0.1`) so `host.docker.internal` works.

## Local run (without Docker)

```bash
# backend1
cd backend1 && cp .env.example .env   # QDRANT_PATH + SQLITE work for local demos
uv sync && uv run uvicorn app.main:app --port 8001

# backend2
cd backend2
# follow that directory's README / requirements for :8002
```

OpenAPI: `http://127.0.0.1:8001/docs`, `http://127.0.0.1:8002/docs`

## API notes

- Required header: `X-Tenant-Id`. backend2 also needs `Authorization: Bearer <JWT>`.
- backend1: `POST /api/v1/ingest`, `GET /api/v1/documents`, `POST /api/v1/retrieve`
- backend2: login / sessions / `/chat/stream` (SSE events: `citation` / `token` / `error` / `done`)

## Frontend

See `frontend/README.md`. Dev server defaults to `:5173`, proxying `/ingest-api` → `:8001` and `/chat-api` → `:8002`.

Chinese README: [README.md](./README.md)
