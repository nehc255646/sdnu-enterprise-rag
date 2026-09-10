# backend · Docker Compose 接入

FastAPI 入库 / 检索 / 鉴权 / 对话，端口 `8000`。

```yaml
backend:
  build: ./backend
  ports:
    - "8000:8000"
  environment:
    DATABASE_URL: postgresql+psycopg2://rag:rag@postgres:5432/rag
    REDIS_URL: redis://redis:6379/0
    QDRANT_URL: http://qdrant:6333
    QDRANT_PATH: ""
    QDRANT_COLLECTION: sdnu_chunks
    EMBEDDING_PROVIDER: ollama
    OLLAMA_BASE_URL: http://host.docker.internal:11434
    OLLAMA_EMBEDDING_MODEL: qwen3-embedding:0.6b
    OPENAI_BASE_URL: http://host.docker.internal:11434/v1
    OPENAI_API_KEY: ${OPENAI_API_KEY:-sk-no-auth}
    OPENAI_MODEL: ${OPENAI_MODEL:-qwen2.5:1.5b}
    JWT_SECRET: ${JWT_SECRET}
    JWT_ALGORITHM: HS256
    UPLOAD_DIR: /app/data/uploads
  extra_hosts:
    - "host.docker.internal:host-gateway"
  depends_on:
    postgres:
      condition: service_healthy
    qdrant:
      condition: service_started
    redis:
      condition: service_healthy
```
