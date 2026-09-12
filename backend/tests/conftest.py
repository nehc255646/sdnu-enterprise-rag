import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_rag.db")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("QDRANT_URL", "")
os.environ.setdefault("QDRANT_PATH", "")
os.environ.setdefault("APP_ENV", "test")


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "auth.db"
    qpath = tmp_path / "qdrant"
    qpath.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_PATH", str(qpath))
    monkeypatch.setenv("QDRANT_URL", "")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setenv("APP_ENV", "test")

    from app.chat.llm_runtime import clear_llm_overrides
    from app.core.cache import reset_redis_cache
    from app.core.config import get_settings
    from app.core.db import reset_engine

    get_settings.cache_clear()
    reset_engine()
    reset_redis_cache()
    clear_llm_overrides()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()
    reset_engine()
    reset_redis_cache()
    clear_llm_overrides()
