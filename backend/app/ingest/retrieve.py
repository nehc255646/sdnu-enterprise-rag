"""Tenant-scoped retrieval with optional Redis cache."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.cache import get_redis
from app.core.config import get_settings
from app.ingest.embeddings import get_embeddings
from app.ingest.qdrant_store import search

logger = logging.getLogger(__name__)


def _generation_key(tenant_id: str) -> str:
    return f"rag:retrieve:gen:{tenant_id}"


def bump_retrieve_generation(tenant_id: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.incr(_generation_key(tenant_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("retrieve generation bump failed: %s", exc)


def _cache_generation(client, tenant_id: str) -> str:
    try:
        return str(client.get(_generation_key(tenant_id)) or "0")
    except Exception:
        return "0"


def _cache_key(tenant_id: str, query: str, top_k: int, doc_type: str | None, generation: str) -> str:
    raw = f"{tenant_id}|{generation}|{query}|{top_k}|{doc_type or ''}"
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
    client = get_redis() if use_cache else None
    generation = _cache_generation(client, tenant_id) if client is not None else "0"
    key = _cache_key(tenant_id, query, top_k, doc_type, generation)
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
