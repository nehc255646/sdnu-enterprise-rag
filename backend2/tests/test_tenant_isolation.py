"""Tenant isolation: different tenants must not see each other's retrieval hits."""

from __future__ import annotations

import pytest

from app.services.retrieval import InMemoryRetrievalClient, QdrantRetrievalClient


def test_inmemory_retrieval_isolates_tenants():
    client = InMemoryRetrievalClient()
    client.add(tenant_id="tenant-a", text="Alice resume: Python FastAPI", document_id="doc-a")
    client.add(tenant_id="tenant-b", text="Bob resume: Java Spring", document_id="doc-b")

    hits_a = client.search(query="Python", tenant_id="tenant-a", top_k=5)
    hits_b = client.search(query="Python", tenant_id="tenant-b", top_k=5)

    assert hits_a, "tenant-a should retrieve its own docs"
    assert all(h["tenant_id"] == "tenant-a" for h in hits_a)
    assert all(h["document_id"] == "doc-a" for h in hits_a)

    # tenant-b must not see Alice's resume even with same query
    assert all(h["tenant_id"] == "tenant-b" for h in hits_b)
    assert not any(h["document_id"] == "doc-a" for h in hits_b)


def test_retrieval_requires_tenant_id():
    client = InMemoryRetrievalClient()
    client.add(tenant_id="t1", text="secret", document_id="d1")
    with pytest.raises(ValueError, match="tenant_id"):
        client.search(query="secret", tenant_id="", top_k=3)


def test_qdrant_client_rejects_empty_tenant():
    client = QdrantRetrievalClient()
    with pytest.raises(ValueError, match="tenant_id"):
        client.search(query="x", tenant_id="  ", top_k=1)


def test_jwt_tenant_in_token():
    from app.core.security import create_access_token, decode_access_token

    token = create_access_token(subject="user-1", tenant_id="tenant-x")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-x"
