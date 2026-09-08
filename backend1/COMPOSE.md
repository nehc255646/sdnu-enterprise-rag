# backend1 · Docker Compose 接入

## Contents

- `backend1/Dockerfile`
- 依赖服务：`postgres`、`qdrant`（必选）；`redis`（可选，不可用时内存队列降级）
- Embedding：宿主机 Ollama（`qwen3-embedding:0.6b`），容器内 `OLLAMA_BASE_URL=http://host.docker.internal:11434`

## 建议环境变量

```yaml
environment:
  DATABASE_URL: postgresql+psycopg2://rag:rag@postgres:5432/rag
  REDIS_URL: redis://redis:6379/0
  QDRANT_URL: http://qdrant:6333
  QDRANT_PATH: ""
  QDRANT_COLLECTION: sdnu_chunks
  EMBEDDING_PROVIDER: ollama
  OLLAMA_BASE_URL: http://host.docker.internal:11434
  OLLAMA_EMBEDDING_MODEL: qwen3-embedding:0.6b
  JWT_SECRET: ${JWT_SECRET}
  JWT_ALGORITHM: HS256
  UPLOAD_DIR: /app/data/uploads
extra_hosts:
  - "host.docker.internal:host-gateway"
ports:
  - "8001:8001"
depends_on:
  postgres:
    condition: service_healthy
  qdrant:
    condition: service_started
```

## 演示语料

仓库根 `knowledge/sdnu/`；首次启动后用 demo JWT + `X-Tenant-Id: sdnu-demo` 调 `POST /api/v1/ingest` 灌入（或挂载后跑脚本）。

## Startup order

1. `postgres` healthy
2. `backend1` healthy (`/api/v1/health`)
3. `backend2` starts and runs shared-schema ensure (`users.hashed_password`)

Both services call idempotent schema ensure after `create_all`, so a missing `hashed_password` column is added automatically.
