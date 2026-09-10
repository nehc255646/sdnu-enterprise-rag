from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "sdnu-rag"
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./rag.db"
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl_seconds: int = 300
    ingest_queue_key: str = "rag:ingest:jobs"

    qdrant_url: str | None = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "sdnu_chunks"
    qdrant_path: str | None = None

    embedding_provider: str = "ollama"
    embedding_model: str = "qwen3-embedding:0.6b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    openai_api_key: str | None = None
    openai_api_base: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"

    openai_base_url: str = "http://127.0.0.1:11434/v1"
    openai_model: str = "qwen2.5:1.5b"

    chunk_size: int = 320
    chunk_overlap: int = 48
    upload_dir: str = "./data/uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    ingest_use_worker: bool = False
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    rag_top_k: int = 5
    rag_history_turns: int = 6

    rate_limit_enabled: bool = True
    rate_limit_chat_per_minute: int = 60
    rate_limit_auth_per_minute: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
