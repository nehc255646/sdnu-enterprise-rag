"""Redis client and rate-limit INCR."""

from __future__ import annotations

import logging
from functools import lru_cache

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
        logger.warning("Redis unavailable: %s", exc)
        return None


def get_redis():
    try:
        return _redis_client()
    except Exception:  # noqa: BLE001
        return None


def reset_redis_cache() -> None:
    _redis_client.cache_clear()


def rate_limit_incr(key: str, window_seconds: int = 60) -> int:
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
