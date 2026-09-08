"""RetrievalClient — tenant-scoped search via ingest HTTP or direct Qdrant.

Collection name defaults to `sdnu_chunks` (shared via QDRANT_COLLECTION).
When ingest holds a local Qdrant path, prefer RETRIEVAL_BACKEND=backend1
so we call POST {backend1}/api/v1/retrieve with forwarded Authorization + X-Tenant-Id.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.cache import cache_get, cache_set, retrieval_cache_key
from app.services.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class RetrievalClient(ABC):
    """Interface for vector retrieval. This service queries only; ingest owns upload."""

    @abstractmethod
    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        doc_type: str | None = None,
        use_cache: bool = True,
        authorization: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return hits; implementations MUST enforce tenant_id filter."""


class Backend1RetrievalClient(RetrievalClient):
    """Call ingest POST /api/v1/retrieve with forwarded Bearer + X-Tenant-Id."""

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        doc_type: str | None = None,
        use_cache: bool = True,
        authorization: str | None = None,
    ) -> list[dict[str, Any]]:
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("tenant_id is required for retrieval")
        tenant_id = str(tenant_id).strip()

        settings = get_settings()
        base = (settings.backend1_base_url or "http://127.0.0.1:8001").rstrip("/")
        url = f"{base}{settings.api_prefix}/retrieve"

        headers: dict[str, str] = {"X-Tenant-Id": tenant_id, "Content-Type": "application/json"}
        if authorization:
            token = authorization if authorization.lower().startswith("bearer ") else f"Bearer {authorization}"
            headers["Authorization"] = token

        body: dict[str, Any] = {"query": query, "top_k": top_k}
        if doc_type:
            body["doc_type"] = doc_type

        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(url, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("backend1 retrieve failed: %s", exc)
            raise

        hits_raw = data.get("hits") or []
        results: list[dict[str, Any]] = []
        for h in hits_raw:
            hit_tenant = h.get("tenant_id")
            if hit_tenant is not None and hit_tenant != tenant_id:
                logger.error("tenant leak blocked from backend1: expected=%s got=%s", tenant_id, hit_tenant)
                continue
            results.append(
                {
                    "score": float(h.get("score") or 0.0),
                    "point_id": str(h.get("point_id") or ""),
                    "text": h.get("text") or "",
                    "document_id": h.get("document_id"),
                    "doc_type": h.get("doc_type"),
                    "chunk_index": h.get("chunk_index"),
                    "filename": h.get("filename"),
                    "tenant_id": hit_tenant or tenant_id,
                }
            )
        return results


class QdrantRetrievalClient(RetrievalClient):
    """Queries Qdrant with a mandatory payload filter on tenant_id."""

    def __init__(self) -> None:
        self._client = None
        self._available = True

    def _get_client(self):
        if self._client is not None:
            return self._client
        settings = get_settings()
        try:
            from qdrant_client import QdrantClient

            if settings.qdrant_path:
                self._client = QdrantClient(path=settings.qdrant_path)
            else:
                url = (settings.qdrant_url or "").strip()
                if not url:
                    raise RuntimeError("Set QDRANT_URL or QDRANT_PATH")
                self._client = QdrantClient(
                    url=url,
                    api_key=settings.qdrant_api_key or None,
                    timeout=2,
                )
                # quick probe
                self._client.get_collections()
            return self._client
        except Exception as exc:  # noqa: BLE001
            logger.warning("Qdrant unavailable: %s", exc)
            self._available = False
            return None

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        doc_type: str | None = None,
        use_cache: bool = True,
        authorization: str | None = None,
    ) -> list[dict[str, Any]]:
        del authorization  # unused for direct Qdrant
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("tenant_id is required for retrieval")

        tenant_id = str(tenant_id).strip()
        key = retrieval_cache_key(tenant_id, query, top_k, doc_type)
        if use_cache:
            cached = cache_get(key)
            if cached is not None:
                # Defense in depth: never return another tenant's cached hits
                return [h for h in cached if h.get("tenant_id") == tenant_id]

        client = self._get_client()
        if client is None:
            return []

        settings = get_settings()
        embeddings = get_embeddings()
        vector = embeddings.embed_query(query)

        from qdrant_client.http import models as qm

        must = [qm.FieldCondition(key="tenant_id", match=qm.MatchValue(value=tenant_id))]
        if doc_type:
            must.append(qm.FieldCondition(key="doc_type", match=qm.MatchValue(value=doc_type)))

        try:
            response = client.query_points(
                collection_name=settings.qdrant_collection,
                query=vector,
                query_filter=qm.Filter(must=must),
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Qdrant search failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for h in response.points:
            payload = h.payload or {}
            # Hard enforce: drop any hit whose payload tenant != requested
            if payload.get("tenant_id") != tenant_id:
                logger.error("tenant leak blocked: expected=%s got=%s", tenant_id, payload.get("tenant_id"))
                continue
            results.append(
                {
                    "score": float(h.score or 0.0),
                    "point_id": str(h.id),
                    "text": payload.get("text", ""),
                    "document_id": payload.get("document_id"),
                    "doc_type": payload.get("doc_type"),
                    "chunk_index": payload.get("chunk_index"),
                    "filename": payload.get("filename"),
                    "tenant_id": payload.get("tenant_id"),
                }
            )

        if use_cache and results:
            cache_set(key, results)
        return results


class RoutingRetrievalClient(RetrievalClient):
    """Prefer ingest HTTP retrieve when configured; fall back to direct Qdrant if server is up."""

    def __init__(self) -> None:
        self._backend1 = Backend1RetrievalClient()
        self._qdrant = QdrantRetrievalClient()

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        doc_type: str | None = None,
        use_cache: bool = True,
        authorization: str | None = None,
    ) -> list[dict[str, Any]]:
        settings = get_settings()
        backend = (settings.retrieval_backend or "backend1").lower().strip()

        if backend == "backend1":
            try:
                return self._backend1.search(
                    query=query,
                    tenant_id=tenant_id,
                    top_k=top_k,
                    doc_type=doc_type,
                    use_cache=use_cache,
                    authorization=authorization,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("backend1 retrieve error, trying Qdrant fallback: %s", exc)
                # Fall through to Qdrant only if HTTP URL looks reachable
                if self._qdrant_http_up():
                    return self._qdrant.search(
                        query=query,
                        tenant_id=tenant_id,
                        top_k=top_k,
                        doc_type=doc_type,
                        use_cache=use_cache,
                        authorization=authorization,
                    )
                raise

        # Explicit qdrant mode
        return self._qdrant.search(
            query=query,
            tenant_id=tenant_id,
            top_k=top_k,
            doc_type=doc_type,
            use_cache=use_cache,
            authorization=authorization,
        )

    def _qdrant_http_up(self) -> bool:
        settings = get_settings()
        url = (settings.qdrant_url or "").strip()
        if not url or settings.qdrant_path:
            return False
        try:
            from qdrant_client import QdrantClient

            qc = QdrantClient(url=url, api_key=settings.qdrant_api_key or None, timeout=1)
            qc.get_collections()
            return True
        except Exception:  # noqa: BLE001
            return False


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
        authorization: str | None = None,
    ) -> list[dict[str, Any]]:
        del use_cache, authorization
        if not tenant_id:
            raise ValueError("tenant_id is required for retrieval")
        q = query.lower()
        hits = []
        for d in self._docs:
            if d["tenant_id"] != tenant_id:
                continue
            if doc_type and d.get("doc_type") != doc_type:
                continue
            if q in d["text"].lower() or True:  # score by simple containment then all
                score = 1.0 if q in d["text"].lower() else 0.1
                hits.append({**d, "score": score})
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:top_k]


@lru_cache
def get_retrieval_client() -> RetrievalClient:
    return RoutingRetrievalClient()
