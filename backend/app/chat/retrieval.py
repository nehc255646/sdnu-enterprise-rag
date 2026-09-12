"""Tenant-scoped search."""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.ingest.retrieve import retrieve as ingest_retrieve


class RetrievalClient(ABC):
    @abstractmethod
    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        doc_type: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Return hits; implementations MUST enforce tenant_id filter."""


class LocalRetrievalClient(RetrievalClient):
    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        doc_type: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("tenant_id is required for retrieval")
        tenant_id = str(tenant_id).strip()
        hits = ingest_retrieve(
            query=query,
            tenant_id=tenant_id,
            top_k=top_k,
            doc_type=doc_type,
            use_cache=use_cache,
        )
        return [h for h in hits if h.get("tenant_id") == tenant_id]


class InMemoryRetrievalClient(RetrievalClient):
    """Test double: stores docs with tenant_id and filters strictly."""

    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []

    def add(self, *, tenant_id: str, text: str, document_id: str = "doc", **extra: Any) -> None:
        self._docs.append(
            {
                "tenant_id": tenant_id,
                "text": text,
                "document_id": document_id,
                "score": 1.0,
                "filename": extra.get("filename", "test.txt"),
                "chunk_index": extra.get("chunk_index", 0),
                "doc_type": extra.get("doc_type", "other"),
                "point_id": extra.get("point_id", f"{tenant_id}-{len(self._docs)}"),
            }
        )

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        doc_type: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        del use_cache
        if not tenant_id:
            raise ValueError("tenant_id is required for retrieval")
        q = query.lower()
        hits = []
        for d in self._docs:
            if d["tenant_id"] != tenant_id:
                continue
            if doc_type and d.get("doc_type") != doc_type:
                continue
            if q in d["text"].lower():
                hits.append({**d, "score": 1.0})
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:top_k]


@lru_cache
def get_retrieval_client() -> RetrievalClient:
    return LocalRetrievalClient()
