# 山师大知识库问答 — chat / auth 服务（backend2）

山东师范大学企业级知识库问答的 **chat & auth** 服务：JWT 鉴权与租户隔离、会话管理、LangChain LCEL RAG 编排、SSE 流式对话。

Ingest/upload 由 ingest 服务提供（默认 `:8001`）；本服务负责 auth / chat。向量检索可走 ingest HTTP 或直连 Qdrant。

## 栈

| 组件 | 选型 |
|------|------|
| API | FastAPI |
| RAG 编排 | LangChain LCEL |
| ORM | SQLAlchemy → Postgres（本地可 SQLite） |
| 缓存 / 限流 | Redis（检索缓存 + chat 限流；Redis 宕机时限流降级为放行） |
| 向量检索 | Qdrant（强制 `tenant_id` payload filter；入库由 ingest 服务） |
| LLM | OpenAI-compatible `ChatOpenAI`（`OPENAI_BASE_URL` + `OPENAI_API_KEY`） |
| Auth | JWT（python-jose）+ `tenant_id` 强制 |

## 快速启动

```bash
# 独立仓库：
cd /workspace/rag-enterprise
# 或 monorepo：
# cd backend2

cp .env.example .env
# 编辑 .env：至少设置 JWT_SECRET；有 LLM 时填 OPENAI_*

# 有 Docker 时启动依赖（与 ingest 服务共用同一套 Postgres/Redis/Qdrant 端口）
docker compose up -d

# 无 Docker 时改 .env：
#   DATABASE_URL=sqlite:///./rag.db
#   QDRANT_PATH=./data/qdrant   # 或留空，检索返回空并降级

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

- Swagger：http://localhost:8002/docs
- OpenAPI JSON：http://localhost:8002/openapi.json
- Health：http://localhost:8002/api/v1/health

依赖宕机时服务仍可启动（DB 回落 SQLite；Redis/Qdrant/LLM 降级），见 health 的 `dependencies`。

## 主要 API

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/auth/register` | `{email, password, tenant_id?}` → JWT |
| POST | `/api/v1/auth/login` | `{email, password, tenant_id}` → `{access_token}` |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET/POST | `/api/v1/sessions` | 列出会话 / 创建会话 |
| GET/DELETE | `/api/v1/sessions/{id}` | 详情（含消息）/ 删除 |
| POST | `/api/v1/chat` | `{session_id, message}` → `{answer, citations[]}` |
| POST | `/api/v1/chat/stream` | SSE：`token` / `citation` / `error` / `done` |
| GET | `/api/v1/health` | 健康检查 |

所有**受保护**业务接口（auth/me、sessions、chat）必须同时带：

```
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>   # 必填；必须与 JWT 载荷中的 tenant_id 一致
```

缺少 `X-Tenant-Id` → `400`；与 token 不一致 → `403`。公开：`/auth/register`、`/auth/login`、`/health`。

### SSE 事件

```
event: citation
data: {"document_id":"...","filename":"...","text":"...","score":0.9}

event: token
data: {"token":"你好"}

event: done
data: {"answer":"..."}

event: error
data: {"message":"..."}
```

## 与 ingest 服务

- 向量集合默认 `sdnu_chunks`，payload 含 `tenant_id`（须与入库侧一致）
- 本服务 **只检索**，不提供 upload/ingest；文档上传请调 ingest 服务 `POST /api/v1/ingest`（默认 `:8001`）
- Embedding 模型需与入库一致（`EMBEDDING_MODEL` / `EMBEDDING_PROVIDER`）
- **JWT 对接**：算法 HS256；claims `sub`=user_id + `tenant_id`；请求头 `Authorization: Bearer` + 必填 `X-Tenant-Id`；共享 `JWT_SECRET` / `JWT_ALGORITHM`。完整说明见 [`docs/jwt-handoff.md`](docs/jwt-handoff.md)

## 租户隔离

1. JWT 载荷强制带 `tenant_id`
2. 受保护路由强制 `Authorization` + **`X-Tenant-Id`**（与 JWT 一致）
3. `get_current_user` / `require_tenant_id` 注入租户
4. `RetrievalClient.search(..., tenant_id=...)` **必须** 带 Qdrant `tenant_id` filter，并二次校验 payload
5. 会话 / 消息查询均按 `tenant_id` + `user_id` 过滤

验收测试：`tests/test_tenant_isolation.py`

```bash
pytest -q
```

## 评测（Ragas）

`tests/test_ragas_sample.py`：

1. **离线 smoke**（始终可跑）：token-overlap faithfulness / context-precision 风格分数。
2. **真跑** `test_ragas_evaluate_live_ollama`：调用真实 `ragas.evaluate`（faithfulness），OpenAI-compat 指向本地 Ollama
   `http://127.0.0.1:11434/v1` · `api_key=sk-no-auth` · `model=qwen2.5:1.5b`（SDNU 校训样例）。
   Ollama/模型不可达时 `pytest.skip`；可达时必须 **pass**（非 stub）。

依赖：`requirements.txt` 已含 `ragas` + `datasets`（亦见 `requirements-eval.txt`；需 `langchain-community<0.4`）。

```bash
pip install -r requirements.txt   # 或 requirements-eval.txt
pytest tests/test_ragas_sample.py -q
```

指针：`evals/ragas_sample.py`。

## 限流与健康

- 配置：`RATE_LIMIT_ENABLED`（默认 true）、`RATE_LIMIT_CHAT_PER_MINUTE`（默认 60）。
- 作用于 `POST /api/v1/chat` 与 `POST /api/v1/chat/stream`（按 tenant+user Redis INCR）。
- Redis 不可达 → **降级放行**（不 500）；超限 → **HTTP 429**。
- Health `dependencies` 含 `rate_limit`：`enabled=… backend=redis|disabled`（optional）。
  Redis 对检索可选（`RETRIEVAL_BACKEND=backend1`），但限流/缓存仅在 Redis 正常时生效。见 `COMPOSE.md`。

## Docker

- `Dockerfile`（python:3.12-slim-bookworm + pip/`requirements.txt`）
- `COMPOSE.md`（Compose 环境变量、depends_on、限流与健康说明）
- `.dockerignore`（排除 `.venv` / `rag.db` / `__pycache__` / `.env`）

详见 `docs/jwt-handoff.md` 与本 README「与 ingest 服务」。

## 目录

```
app/
  api/         # auth, sessions, chat, health
  core/        # config, security (JWT), deps
  db/          # session + models (User, Document, ChunkMeta, ChatSession, ChatMessage)
  schemas/     # Pydantic / OpenAPI
  services/    # retrieval, rag_chain (LCEL), cache
docker-compose.yml
tests/
```

## 配置（环境变量）

见 `.env.example`：`DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, `OPENAI_*`, `JWT_SECRET`, `EMBEDDING_*`, `RATE_LIMIT_*` 等。**禁止把密钥写入代码仓库。** Compose 建议见 `COMPOSE.md`。
