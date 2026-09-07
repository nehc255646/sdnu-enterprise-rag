from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "rag-backend1"
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./rag.db"
    redis_url: str = "redis://localhost:6379/0"
    ingest_queue_key: str = "rag:ingest:jobs"

    qdrant_url: str | None = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "sdnu_chunks"
    qdrant_path: str | None = None  # local disk mode when Docker unavailable

    embedding_provider: str = "ollama"  # ollama | openai | huggingface | hash
    embedding_model: str = "qwen3-embedding:0.6b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    openai_api_key: str | None = None
    openai_api_base: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"

    chunk_size: int = 320
    chunk_overlap: int = 48
    upload_dir: str = "./data/uploads"

    # JWT (shared with 后端2 — see backend2/docs/jwt-handoff.md)
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"


@lru_cache
def get_settings() -> Settings:
    return Settings()
