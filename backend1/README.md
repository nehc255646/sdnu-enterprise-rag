# Ingest & Retrieval Service

文档入库与向量检索服务：解析 / 切分 / 向量化、租户隔离检索。面向「山东师范大学」等知识库场景。

## Stack

| Component | Choice |
|-----------|--------|
| API | FastAPI |
| Split / load | LangChain |
| Metadata | SQLAlchemy → Postgres（本地可用 SQLite） |
| Queue / cache | Redis（可选） |
| Vectors | Qdrant（payload 含 `tenant_id`） |

LLM 对话与签发 JWT 不在本服务范围（见 `backend2/`）。

## Quick start

```bash
cp .env.example .env
# With Docker infra from repo root: docker compose up -d
# Without Docker, set in .env:
#   DATABASE_URL=sqlite:///./rag.db
#   QDRANT_PATH=./data/qdrant-b1
#   QDRANT_URL=

uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Optional ingest worker:

```bash
uv run python -m app.workers.ingest_worker
```

OpenAPI: `http://localhost:8001/docs`

## Auth

Protected routes require:

```
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant>
```

JWT is HS256 with claims `sub` and `tenant_id`. Share `JWT_SECRET` with the chat service（详见 `backend2/docs/jwt-handoff.md`）.

- missing / invalid token → 401
- missing `X-Tenant-Id` → 400 / 422
- header tenant ≠ token `tenant_id` → 403

`GET /api/v1/health` is public.

## API

- `GET /api/v1/health`
- `GET /api/v1/documents`
- `POST /api/v1/ingest` — multipart: `file`, `doc_type` (`kb|resume|jd|internship|other`), `sync`
- `GET /api/v1/ingest/{document_id}`
- `POST /api/v1/retrieve` — JSON: `{ "query", "top_k", "doc_type?" }`

## Tenant isolation

Qdrant queries always filter on `tenant_id`. Documents are scoped the same way in Postgres.

## Embedding (Ollama)

```
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

Vector size is **1024**. After changing the embedding model, recreate the collection and re-ingest. The chat service must use the same model and dimension for query-time embedding if it embeds locally; preferred path is calling this service's `/retrieve`.
