# RAG Enterprise — 后端2 (Auth / Sessions / Chat Orchestration)

企业级实习简历知识库 RAG 的 **后端2** 服务：JWT 鉴权与租户隔离、会话管理、LangChain LCEL RAG 编排、SSE 流式对话。

> **分工**  
> - **后端1**（`rag-backend1`）：文档上传 / 切分 / 向量入库（Qdrant ingest）  
> - **后端2**（本仓库）：auth / tenant / chat sessions / retrieve→prompt→LLM  
> - **前端**：调用本服务的 auth + chat；上传走后端1

## 栈

| 组件 | 选型 |
|------|------|
| API | FastAPI |
| RAG 编排 | LangChain LCEL（**不用** LlamaIndex） |
| ORM | SQLAlchemy → Postgres（本地可 SQLite） |
| 缓存 | Redis（检索结果缓存 + 可选限流 key） |
| 向量检索 | Qdrant（强制 `tenant_id` payload filter；入库由后端1） |
| LLM | OpenAI-compatible `ChatOpenAI`（`OPENAI_BASE_URL` + `OPENAI_API_KEY`） |
| Auth | JWT（python-jose）+ `tenant_id` 强制 |

## 快速启动

```bash
cd /workspace/rag-enterprise
cp .env.example .env
# 编辑 .env：至少设置 JWT_SECRET；有 LLM 时填 OPENAI_* 

# 有 Docker 时启动依赖（与后端1共用同一套 Postgres/Redis/Qdrant 端口）
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

## 主要 API（给前端）

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

## 与后端1协作

- 向量集合默认 `sdnu_chunks`，payload 含 `tenant_id`（与后端1一致）
- 本服务 **只检索**，不提供 upload/ingest；前端上传请调后端1 `POST /api/v1/ingest`
- Embedding 模型需与后端1入库一致（`EMBEDDING_MODEL` / `EMBEDDING_PROVIDER`）

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

最小可跳过样例：`tests/test_ragas_sample.py`（`pytest.importorskip("ragas")`；未安装 ragas 时跳过，仍文档化评测路径）。

```bash
# 可选：pip install ragas datasets
pytest tests/test_ragas_sample.py -q
```

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

见 `.env.example`：`DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `JWT_SECRET`, `EMBEDDING_MODEL` 等。**禁止把密钥写入代码仓库。**
