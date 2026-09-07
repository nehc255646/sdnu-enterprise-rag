"""Tenant isolation + JWT smoke."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt


class FakeEmbeddings:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        vec = [0.0] * 8
        for i, ch in enumerate(text.encode("utf-8")[:64]):
            vec[i % 8] += (ch % 31) / 31.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


def _token(tenant_id: str, secret: str = "change-me-to-a-long-random-string") -> str:
    return jwt.encode({"sub": "u1", "tenant_id": tenant_id}, secret, algorithm="HS256")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "rag.db"
    qpath = tmp_path / "qdrant"
    qpath.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_PATH", str(qpath))
    monkeypatch.setenv("QDRANT_URL", "")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("JWT_SECRET", "change-me-to-a-long-random-string")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")

    from app.core.config import get_settings
    from app.core import db as dbmod
    from app.services import embeddings as embmod
    from app.services import qdrant_store as qmod

    get_settings.cache_clear()
    embmod.get_embeddings.cache_clear()
    qmod.get_qdrant.cache_clear()

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


def test_health_public(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_missing_auth_401(client: TestClient):
    r = client.get("/api/v1/documents", headers={"X-Tenant-Id": "tenant-a"})
    assert r.status_code == 401


def test_missing_tenant_400(client: TestClient):
    r = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {_token('t')}"})
    assert r.status_code in (400, 422)


def test_tenant_mismatch_403(client: TestClient):
    r = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {_token('tenant-a')}", "X-Tenant-Id": "tenant-b"},
    )
    assert r.status_code == 403


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
            headers={"X-Tenant-Id": "tenant-a", "Authorization": f"Bearer {_token('tenant-a')}"},
            data={"doc_type": "kb", "sync": "true"},
            files={"file": ("alice_resume.txt", f, "text/plain")},
        )
    assert r.status_code == 200, r.text

    hit_a = client.post(
        "/api/v1/retrieve",
        headers={"X-Tenant-Id": "tenant-a", "Authorization": f"Bearer {_token('tenant-a')}"},
        json={"query": "FastAPI LangChain internship Acme", "top_k": 3},
    )
    assert hit_a.status_code == 200
    assert len(hit_a.json()["hits"]) >= 1

    hit_b = client.post(
        "/api/v1/retrieve",
        headers={"X-Tenant-Id": "tenant-b", "Authorization": f"Bearer {_token('tenant-b')}"},
        json={"query": "FastAPI LangChain internship Acme", "top_k": 3},
    )
    assert hit_b.status_code == 200
    assert hit_b.json()["hits"] == []
