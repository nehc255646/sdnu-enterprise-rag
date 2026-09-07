# RAG Backend1 — Ingest & Retrieval

企业级实习简历知识库 RAG 的 **后端1** 服务：文档入库、向量检索、租户隔离。

## 栈

| 组件 | 选型 |
|------|------|
| API | FastAPI |
| 编排/切分 | LangChain + RecursiveCharacterTextSplitter |
| 元数据 | SQLAlchemy → Postgres（本地可 SQLite） |
| 队列/缓存 | Redis |
| 向量库 | Qdrant（payload 含 `tenant_id`） |

**不在本服务范围**：JWT 鉴权 / LLM 生成链（后端2）、前端页面。

## 快速启动

```bash
cp .env.example .env
# 有 Docker 时：
docker compose up -d
# 无 Docker 时改 .env：
#   DATABASE_URL=sqlite:///./rag.db
#   QDRANT_PATH=./data/qdrant
#   QDRANT_URL=

uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

可选独立 worker：

```bash
uv run python -m app.workers.ingest_worker
```

OpenAPI：`http://localhost:8001/docs`

## 鉴权约定（给后端2 / 前端）

所有业务接口必须带请求头：

```
X-Tenant-Id: <tenant>
```

后端2 上线 JWT 后可改为从 token 解析 `tenant_id`，本服务已按租户过滤。

## 主要 API

- `GET /api/v1/health`
- `POST /api/v1/ingest` — multipart：`file`, `doc_type`(`resume|jd|internship|other`), `sync`(bool)
- `GET /api/v1/ingest/{document_id}`
- `POST /api/v1/retrieve` — JSON：`{ "query", "top_k", "doc_type?" }`

## 租户隔离

Qdrant 检索强制 `tenant_id` payload filter；Postgres 查询按 `tenant_id` 校验。验收：租户 A 入库后，租户 B 同 query 命中为空。

## 目录

```
app/
  api/          # routes + schemas
  core/         # config, db
  models/       # SQLAlchemy
  services/     # ingest, retrieve, qdrant, embeddings, redis
  workers/      # Redis ingest worker
docker-compose.yml
```
