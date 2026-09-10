# 山师大知识库问答

文档入库、向量检索与 RAG 对话：JWT 鉴权、租户隔离、SSE 引用溯源。

## 栈

| 组件 | 选型 |
|------|------|
| API | FastAPI |
| 切分 / 编排 | LangChain（LCEL） |
| ORM | SQLAlchemy → Postgres（本地可 SQLite） |
| 缓存 / 队列 / 限流 | Redis（检索缓存 + 入库队列 + 聊天限流；Redis 宕机时限流降级） |
| 向量 | Qdrant（强制 `tenant_id` payload filter） |
| Embedding | Ollama `qwen3-embedding:0.6b`（1024 维；入库与查询同模） |
| LLM | OpenAI 兼容 `ChatOpenAI` |
| Auth | JWT（HS256）+ `tenant_id` |

## 快速启动

```bash
cp .env.example .env
uv sync --extra dev
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- Swagger：http://127.0.0.1:8000/docs
- Health：http://127.0.0.1:8000/api/v1/health

## 主要 API

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/ingest` | 上传入库（`file` + `doc_type` + `sync`） |
| GET | `/api/v1/documents` | 文档列表 |
| GET | `/api/v1/ingest/{id}` | 入库状态 |
| POST | `/api/v1/retrieve` | `{ query, top_k, doc_type? }` |
| POST | `/api/v1/auth/register` | `{email, password, tenant_id?}` → JWT |
| POST | `/api/v1/auth/login` | `{email, password, tenant_id}` → `{access_token}` |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET/POST | `/api/v1/sessions` | 列出会话 / 创建会话 |
| GET/DELETE | `/api/v1/sessions/{id}` | 详情（含消息）/ 删除 |
| POST | `/api/v1/chat` | `{session_id, message}` → `{answer, citations[]}` |
| POST | `/api/v1/chat/stream` | SSE：`citation` → `token`* → `done`（或 `error`） |
| GET/PUT | `/api/v1/llm/config` | OpenAI 兼容三元组热切换 |
| GET | `/api/v1/health` | 健康检查 |

受保护接口必须同时带：

```
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

缺少 `X-Tenant-Id` → `400` / `422`；与 JWT 不一致 → `403`。公开：`/auth/register`、`/auth/login`、`/health`。

入库 / 文档 / retrieve 只校验 JWT 与租户头；会话 / 聊天 / `/me` / LLM 配置还要求 `users` 表中存在该用户。

## 租户隔离

1. JWT 载荷强制带 `tenant_id`
2. 受保护路由强制 `Authorization` + `X-Tenant-Id`（与 JWT 一致）
3. Qdrant 查询带 `tenant_id` filter，并二次校验 payload
4. 会话 / 消息按 `tenant_id` + `user_id` 过滤

```bash
uv run pytest -q
```

## Embedding

```
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

向量维度 **1024**。更换模型后需重建集合并重新入库。

## 评测（Ragas）

`tests/test_ragas_sample.py`：离线 smoke 始终可跑；live 需 `uv sync --extra eval` 与本地 Ollama。

```bash
uv run pytest tests/test_ragas_sample.py -q
```
