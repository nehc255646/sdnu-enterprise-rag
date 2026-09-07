"""Tenant isolation smoke: retrieve must not leak across tenants."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Force local SQLite + local Qdrant before app import side effects
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_rag.db"
os.environ["QDRANT_PATH"] = "./data/test_qdrant"
os.environ["QDRANT_URL"] = ""
os.environ["EMBEDDING_PROVIDER"] = "huggingface"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"  # force memory fallback


class FakeEmbeddings:
    """Deterministic tiny vectors — no model download."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        # crude bag-of-chars fingerprint in 8 dims
        vec = [0.0] * 8
        for i, ch in enumerate(text.encode("utf-8")[:64]):
            vec[i % 8] += (ch % 31) / 31.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "rag.db"
    qpath = tmp_path / "qdrant"
    qpath.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_PATH", str(qpath))
    monkeypatch.setenv("QDRANT_URL", "")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    from app.core.config import get_settings
    from app.core import db as dbmod
    from app.services import embeddings as embmod
    from app.services import qdrant_store as qmod

    get_settings.cache_clear()
    embmod.get_embeddings.cache_clear()
    qmod.get_qdrant.cache_clear()

    # rebuild engine for new DATABASE_URL
    dbmod.engine = dbmod._engine()
    dbmod.SessionLocal.configure(bind=dbmod.engine)

    with patch("app.services.embeddings.build_embeddings", return_value=FakeEmbeddings()), patch(
        "app.services.ingest.get_embeddings", return_value=FakeEmbeddings()
    ), patch("app.services.retrieve.get_embeddings", return_value=FakeEmbeddings()):
        from app.main import create_app

        app = create_app()
        with TestClient(app) as c:
            yield c

    get_settings.cache_clear()
    embmod.get_embeddings.cache_clear()
    qmod.get_qdrant.cache_clear()


def test_cross_tenant_no_leak(client: TestClient):
    sample = Path("tests/fixtures/alice_resume.txt")
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "Alice Chen interned at Acme Corp building FastAPI microservices and LangChain RAG pipelines.",
        encoding="utf-8",
    )

    with sample.open("rb") as f:
        r = client.post(
            "/api/v1/ingest",
            headers={"X-Tenant-Id": "tenant-a"},
            data={"doc_type": "resume", "sync": "true"},
            files={"file": ("alice_resume.txt", f, "text/plain")},
        )
    assert r.status_code == 200, r.text
    assert r.json()["document_id"]

    hit_a = client.post(
        "/api/v1/retrieve",
        headers={"X-Tenant-Id": "tenant-a"},
        json={"query": "FastAPI LangChain internship Acme", "top_k": 3},
    )
    assert hit_a.status_code == 200
    assert len(hit_a.json()["hits"]) >= 1

    hit_b = client.post(
        "/api/v1/retrieve",
        headers={"X-Tenant-Id": "tenant-b"},
        json={"query": "FastAPI LangChain internship Acme", "top_k": 3},
    )
    assert hit_b.status_code == 200
    assert hit_b.json()["hits"] == []


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
