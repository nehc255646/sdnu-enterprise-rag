# 了解山东师范大学 · 企业级 RAG

主题：山东师范大学知识库问答。多租户（`tenant_id` / `X-Tenant-Id`），演示租户：`sdnu-demo`。

## 结构

| 目录 | 职责 | 默认端口 |
|------|------|----------|
| `backend1/` | Ingest + 向量检索（FastAPI + LangChain + Qdrant） | `:8001` |
| `backend2/` | 鉴权 / 会话 / 对话 SSE（FastAPI + LangChain LCEL） | `:8002` |
| `frontend/` | 文档管理 + 知识库对话（React/Vite/Ant Design） | `:5173` |

## 栈

- FastAPI + LangChain
- SQLAlchemy（Postgres / 本地 SQLite）
- Redis（缓存 / 队列）
- Qdrant collection：`sdnu_chunks`
- 密钥走环境变量（见各服务 `.env.example`）

## 快速启动（本机无 Docker 时）

```bash
# backend1
cd backend1 && cp .env.example .env   # 可用 QDRANT_PATH + SQLITE
uv sync && uv run uvicorn app.main:app --port 8001

# backend2
cd backend2
# 按该目录 README / requirements 启动 :8002
```

OpenAPI：`http://127.0.0.1:8001/docs`、`http://127.0.0.1:8002/docs`

## 契约要点

- 业务请求头：`X-Tenant-Id`（必填）；后端2 另需 `Authorization: Bearer <JWT>`
- 后端1：`POST /api/v1/ingest`、`GET /api/v1/documents`、`POST /api/v1/retrieve`
- 后端2：登录 / 会话 / `/chat/stream`（SSE：`citation`/`token`/`error`/`done`）

## Frontend

见 `frontend/README.md`。开发服务器默认 `:5173`，代理 `/ingest-api`→`:8001`、`/chat-api`→`:8002`。
