# backend2 · compose 接入说明（给 @计划）

## 产物

- `backend2/Dockerfile`（Python 3.12 slim + `requirements.txt` / pip，非 uv）
- 依赖服务：`backend1`、`postgres`、`redis`（必选 depends_on）；`qdrant` **可选**（当 `RETRIEVAL_BACKEND=backend1` 时检索走后端1，不直连 Qdrant）
- LLM / Embedding：宿主机 Ollama（`qwen2.5:1.5b` + `qwen3-embedding:0.6b`），容器内经 `host.docker.internal`

## 建议环境变量

```yaml
environment:
  DATABASE_URL: postgresql+psycopg2://rag:rag@postgres:5432/rag
  REDIS_URL: redis://redis:6379/0
  BACKEND1_BASE_URL: http://backend1:8001
  RETRIEVAL_BACKEND: backend1
  OPENAI_BASE_URL: http://host.docker.internal:11434/v1
  OPENAI_API_KEY: sk-no-auth
  OPENAI_MODEL: qwen2.5:1.5b
  EMBEDDING_PROVIDER: ollama
  OLLAMA_BASE_URL: http://host.docker.internal:11434
  OLLAMA_EMBEDDING_MODEL: qwen3-embedding:0.6b
  JWT_SECRET: ${JWT_SECRET}   # 必须与 backend1 共享
  JWT_ALGORITHM: HS256
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_CHAT_PER_MINUTE: "60"
extra_hosts:
  - "host.docker.internal:host-gateway"
ports:
  - "8002:8002"
depends_on:
  backend1:
    condition: service_started
  postgres:
    condition: service_healthy
  redis:
    condition: service_started
```

## Redis / 限流行为

- Redis 用于：**检索结果缓存** + **chat 限流**（`/api/v1/chat`、`/api/v1/chat/stream`）。
- Redis 不可达时 **降级允许请求**（不 500）；health 中 `redis` / `rate_limit` 标为 optional/disabled。
- 限流仅在 Redis 可用且 `RATE_LIMIT_ENABLED=true` 时生效；超限 → HTTP **429**。
- `RETRIEVAL_BACKEND=backend1` 时 Qdrant 对 backend2 可选；Redis 红灯不阻断检索，但限流与缓存失效。

## 健康检查要点

`GET /api/v1/health` 暴露 `rate_limit` 依赖：`enabled`、`backend=redis|disabled`（见 dependencies detail）。
