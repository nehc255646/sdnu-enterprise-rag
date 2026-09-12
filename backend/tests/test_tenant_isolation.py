"""Tenant isolation + JWT smoke (ingest retrieve + chat retrieval doubles)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.chat.retrieval import InMemoryRetrievalClient, LocalRetrievalClient
from app.core.security import create_access_token, decode_access_token


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


def _headers(token: str, tenant_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id}


def _ingest_alice(client: TestClient, token: str, tenant_id: str) -> None:
    sample = Path("tests/fixtures/alice_resume.txt")
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "Alice Chen interned at Acme Corp building FastAPI microservices and LangChain RAG pipelines.",
        encoding="utf-8",
    )
    with sample.open("rb") as f:
        r = client.post(
            "/api/v1/ingest",
            headers=_headers(token, tenant_id),
            data={"doc_type": "kb", "sync": "true"},
            files={"file": ("alice_resume.txt", f, "text/plain")},
        )
    assert r.status_code == 200, r.text


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
    monkeypatch.setenv("APP_ENV", "test")

    from app.core.cache import reset_redis_cache
    from app.core.config import get_settings
    from app.core.db import reset_engine
    from app.ingest import embeddings as embmod
    from app.ingest import qdrant_store as qmod

    get_settings.cache_clear()
    reset_engine()
    reset_redis_cache()
    embmod.get_embeddings.cache_clear()
    qmod.get_qdrant.cache_clear()

    with patch("app.ingest.embeddings.build_embeddings", return_value=FakeEmbeddings()), patch(
        "app.ingest.pipeline.get_embeddings", return_value=FakeEmbeddings()
    ), patch("app.ingest.retrieve.get_embeddings", return_value=FakeEmbeddings()):
        from app.main import create_app

        app = create_app()
        with TestClient(app) as c:
            yield c

    get_settings.cache_clear()
    reset_engine()
    reset_redis_cache()
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
    assert r.status_code == 400


def test_local_client_drops_missing_tenant(monkeypatch):
    def fake_retrieve(**_kwargs):
        return [
            {"tenant_id": "t1", "text": "keep"},
            {"tenant_id": None, "text": "drop-none"},
            {"tenant_id": "t2", "text": "drop-other"},
        ]

    monkeypatch.setattr("app.chat.retrieval.ingest_retrieve", fake_retrieve)
    hits = LocalRetrievalClient().search(query="x", tenant_id="t1", top_k=5)
    assert hits == [{"tenant_id": "t1", "text": "keep"}]


def test_tenant_mismatch_403(client: TestClient):
    r = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {_token('tenant-a')}", "X-Tenant-Id": "tenant-b"},
    )
    assert r.status_code == 403


def test_cross_tenant_no_leak(client: TestClient):
    _ingest_alice(client, _token("tenant-a"), "tenant-a")

    hit_a = client.post(
        "/api/v1/retrieve",
        headers=_headers(_token("tenant-a"), "tenant-a"),
        json={"query": "FastAPI LangChain internship Acme", "top_k": 3},
    )
    assert hit_a.status_code == 200
    assert len(hit_a.json()["hits"]) >= 1

    hit_b = client.post(
        "/api/v1/retrieve",
        headers=_headers(_token("tenant-b"), "tenant-b"),
        json={"query": "FastAPI LangChain internship Acme", "top_k": 3},
    )
    assert hit_b.status_code == 200
    assert hit_b.json()["hits"] == []


def test_health_after_ingest(client: TestClient):
    _ingest_alice(client, _token("tenant-a"), "tenant-a")
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    qdrant = next(d for d in r.json()["dependencies"] if d["name"] == "qdrant")
    assert qdrant["ok"] is True


def test_seed_jwt_can_ingest_but_not_chat(client: TestClient):
    seed = _token("tenant-a")
    headers = _headers(seed, "tenant-a")
    docs = client.get("/api/v1/documents", headers=headers)
    assert docs.status_code == 200
    sessions = client.get("/api/v1/sessions", headers=headers)
    assert sessions.status_code == 401
    chat = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"session_id": "00000000-0000-0000-0000-000000000000", "message": "hi"},
    )
    assert chat.status_code == 401


def test_registered_user_chat_uses_ingest_hits(client: TestClient):
    email = "alice@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1", "tenant_id": "tenant-a"},
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = _headers(token, "tenant-a")
    _ingest_alice(client, token, "tenant-a")

    sess = client.post("/api/v1/sessions", headers=headers, json={"title": "t"})
    assert sess.status_code == 201, sess.text
    with patch("app.chat.rag_chain.get_llm", side_effect=RuntimeError("llm disabled in test")):
        chat = client.post(
            "/api/v1/chat",
            headers=headers,
            json={"session_id": sess.json()["id"], "message": "FastAPI LangChain internship Acme"},
        )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["citations"], body
    blob = " ".join((c.get("filename") or "") + " " + (c.get("text") or "") for c in body["citations"])
    assert "alice_resume.txt" in blob or "FastAPI" in blob


def test_invalid_tenant_path_400(client: TestClient):
    tok = _token("../tmp")
    r = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {tok}", "X-Tenant-Id": "../tmp"},
    )
    assert r.status_code == 400


def test_legacy_doc_rejected(client: TestClient):
    r = client.post(
        "/api/v1/ingest",
        headers={"X-Tenant-Id": "tenant-a", "Authorization": f"Bearer {_token('tenant-a')}"},
        data={"doc_type": "kb", "sync": "true"},
        files={"file": ("legacy.doc", b"not-a-real-doc", "application/msword")},
    )
    assert r.status_code == 400


def test_inmemory_retrieval_isolates_tenants():
    client = InMemoryRetrievalClient()
    client.add(tenant_id="tenant-a", text="Alice resume: Python FastAPI", document_id="doc-a")
    client.add(tenant_id="tenant-b", text="Bob resume: Java Spring", document_id="doc-b")

    hits_a = client.search(query="Python", tenant_id="tenant-a", top_k=5)
    hits_b = client.search(query="Python", tenant_id="tenant-b", top_k=5)

    assert hits_a, "tenant-a should retrieve its own docs"
    assert all(h["tenant_id"] == "tenant-a" for h in hits_a)
    assert all(h["document_id"] == "doc-a" for h in hits_a)

    assert all(h["tenant_id"] == "tenant-b" for h in hits_b)
    assert not any(h["document_id"] == "doc-a" for h in hits_b)


def test_retrieval_requires_tenant_id():
    client = InMemoryRetrievalClient()
    client.add(tenant_id="t1", text="secret", document_id="d1")
    with pytest.raises(ValueError, match="tenant_id"):
        client.search(query="secret", tenant_id="", top_k=3)


def test_local_client_rejects_empty_tenant():
    client = LocalRetrievalClient()
    with pytest.raises(ValueError, match="tenant_id"):
        client.search(query="x", tenant_id="  ", top_k=1)


def test_jwt_tenant_in_token():
    token = create_access_token(subject="user-1", tenant_id="tenant-x")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-x"
