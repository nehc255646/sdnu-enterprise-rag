"""Redis cache for retrieval results (+ optional rate-limit key helpers)."""

from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _redis_client():
    settings = get_settings()
    try:
        import redis

        client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable, cache disabled: %s", exc)
        return None


def get_redis():
    """Return Redis client or None if unreachable (graceful degrade)."""
    try:
        return _redis_client()
    except Exception:  # noqa: BLE001
        return None


def reset_redis_cache() -> None:
    _redis_client.cache_clear()


def retrieval_cache_key(tenant_id: str, query: str, top_k: int, doc_type: str | None = None) -> str:
    raw = f"{tenant_id}|{query}|{top_k}|{doc_type or ''}"
    return "rag:retrieve:" + hashlib.sha256(raw.encode()).hexdigest()


def cache_get(key: str) -> Any | None:
    client = get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache get failed: %s", exc)
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    client = get_redis()
    if client is None:
        return
    settings = get_settings()
    ttl = ttl if ttl is not None else settings.redis_cache_ttl_seconds
    try:
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache set failed: %s", exc)


def rate_limit_incr(key: str, window_seconds: int = 60) -> int:
    """Optional rate-limit helper using Redis INCR + EXPIRE."""
    client = get_redis()
    if client is None:
        return 0
    try:
        n = client.incr(key)
        if n == 1:
            client.expire(key, window_seconds)
        return int(n)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate limit incr failed: %s", exc)
        return 0
