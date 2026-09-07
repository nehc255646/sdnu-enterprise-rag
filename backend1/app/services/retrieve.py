"""Tenant-scoped retrieval with optional Redis cache."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.config import get_settings
from app.services.embeddings import get_embeddings
from app.services.qdrant_store import search
from app.services.redis_queue import get_redis

logger = logging.getLogger(__name__)


def _cache_key(tenant_id: str, query: str, top_k: int, doc_type: str | None) -> str:
    raw = f"{tenant_id}|{query}|{top_k}|{doc_type or ''}"
    return "rag:retrieve:" + hashlib.sha256(raw.encode()).hexdigest()


def retrieve(
    *,
    query: str,
    tenant_id: str,
    top_k: int = 5,
    doc_type: str | None = None,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    settings = get_settings()
    key = _cache_key(tenant_id, query, top_k, doc_type)
    client = get_redis() if use_cache else None
    if client is not None:
        cached = client.get(key)
        if cached:
            return json.loads(cached)

    embeddings = get_embeddings()
    vector = embeddings.embed_query(query)
    results = search(
        query_vector=vector,
        tenant_id=tenant_id,
        top_k=top_k,
        doc_type=doc_type,
        settings=settings,
    )

    if client is not None:
        try:
            client.setex(key, 300, json.dumps(results, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache write failed: %s", exc)
    return results
