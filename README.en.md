# SDNU Enterprise RAG

中文: [README.md](./README.md)

Multi-tenant RAG: FastAPI + LangChain + Qdrant, SSE citation provenance, same-model Ollama embedding, one-click Compose / `start.sh` demo.

Demo tenant **`sdnu-demo`** · corpus `knowledge/sdnu/` (~**16** documents).

## Tech stack

- **Backend**: FastAPI · LangChain (LCEL) · JWT auth
- **Frontend**: React · Vite · Ant Design
- **Data**: Postgres · Redis · Qdrant (collection `sdnu_chunks`)
- **Models**: Ollama `qwen3-embedding:0.6b` (**1024-d**) · OpenAI-compatible chat (default `qwen2.5:1.5b`)
- **Ops**: Docker Compose · `start.sh` local one-click start

## Highlights

| Capability | Detail |
|------------|--------|
| Service split | `backend1` (`:8001`) ingest / retrieve; `backend2` (`:8002`) auth / sessions / RAG chat; retrieval decoupled via HTTP `POST /retrieve` |
| Multi-tenant isolation | Protected routes require `X-Tenant-Id` matching JWT `tenant_id`; Qdrant payloads and Postgres rows scoped the same way |
| LangChain RAG | Retrieve → generate with citations; chat side orchestrated with LCEL |
| SSE citation provenance | `/api/v1/chat/stream`: `citation` → `token`* → `done` (or `error`); answers trace back to concrete chunks |
| Same-model embedding | Ingest and query both use Ollama `qwen3-embedding:0.6b`, **1024-d**, no dimension drift |
| Hot-swappable LLM | OpenAI-compatible triple `base_url` / `model` / `api_key` via `GET\|PUT /api/v1/llm/config` — no restart |
| One-click demo | `docker compose up --build` or `./start.sh` (Postgres + Redis + Qdrant + both backends + frontend) |
| Ragas eval | `backend2/evals` + `pytest tests/test_ragas_sample.py` (offline smoke / optional live Ollama) |
| Rate limit fail-open | Redis chat rate limit (default 60/min); if Redis is down, allow (no 500); over limit → **429** |

## Architecture

```mermaid
flowchart LR
  Browser[Browser]
  FE[frontend :5173]
  B1[backend1 :8001]
  B2[backend2 :8002]
  PG[(Postgres)]
  RD[(Redis)]
  QD[(Qdrant)]
  OL[Ollama :11434]

  Browser --> FE
  FE -->|/ingest-api| B1
  FE -->|/chat-api| B2
  B2 -->|POST /retrieve| B1
  B1 --> PG & RD & QD
  B2 --> PG & RD
  B1 -->|embed| OL
  B2 -->|ChatOpenAI /v1| OL
```

## Quick start

Prerequisites: [Ollama](https://ollama.com) on the host, then pull:

```bash
ollama pull qwen3-embedding:0.6b
ollama pull qwen2.5:1.5b
```

**Option A — Compose**

```bash
cp .env.example .env   # set JWT_SECRET (shared by backend1 and backend2)
docker compose up -d --build
```

**Option B — local `start.sh`**

```bash
./start.sh          # Postgres + Qdrant (Docker) + host Redis / Ollama + both backends + frontend
./start.sh stop
```

| Surface | URL |
|---------|-----|
| Frontend | http://127.0.0.1:5173 |
| backend1 OpenAPI | http://127.0.0.1:8001/docs |
| backend2 OpenAPI | http://127.0.0.1:8002/docs |

**First ingest**: Compose / `start.sh` do **not** auto-ingest. Register/login as tenant `sdnu-demo`, upload files from `knowledge/sdnu/` on the documents page (prefer `sync=true` for these small txts), or call `POST /api/v1/ingest` on `:8001` with `Authorization` + `X-Tenant-Id: sdnu-demo`.

## Ports & key APIs

| Service | Port | Role |
|---------|------|------|
| frontend | `5173` | UI (`/ingest-api` → b1, `/chat-api` → b2) |
| backend1 | `8001` | `POST /ingest` · `POST /retrieve` · document list |
| backend2 | `8002` | Auth · sessions · `POST /chat` · `POST /chat/stream` · hot LLM config |
| Qdrant | `6333` | Vectors, collection `sdnu_chunks` |

Protected headers: `Authorization: Bearer <JWT>` + `X-Tenant-Id: sdnu-demo`.

## Scope

Portfolio / demo project: public-style SDNU corpus + multi-tenant RAG pipeline. **Not** an official university system. Emblem attribution: [frontend/public/ATTRIBUTION.md](./frontend/public/ATTRIBUTION.md).

中文: [README.md](./README.md)
