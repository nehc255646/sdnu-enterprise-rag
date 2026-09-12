"""Chat/auth rate limiting via Redis INCR, with process-local fallback."""

from __future__ import annotations

import logging
import time
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.cache import get_redis, rate_limit_incr
from app.core.config import get_settings
from app.core.deps import CurrentUser

logger = logging.getLogger(__name__)

_local_lock = Lock()
_local_buckets: dict[str, tuple[int, float]] = {}


def _local_incr(key: str, window_seconds: int = 60) -> int:
    now = time.monotonic()
    with _local_lock:
        count, start = _local_buckets.get(key, (0, now))
        if now - start >= window_seconds:
            count, start = 0, now
        count += 1
        _local_buckets[key] = (count, start)
        return count


def _incr(key: str, window_seconds: int = 60) -> int:
    try:
        n = rate_limit_incr(key, window_seconds=window_seconds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis rate limit failed, using local: %s", exc)
        n = 0
    if n == 0:
        return _local_incr(key, window_seconds)
    return n


def rate_limit_status() -> dict:
    settings = get_settings()
    enabled = bool(settings.rate_limit_enabled)
    if not enabled:
        return {"enabled": False, "backend": "disabled", "ok": True, "detail": "RATE_LIMIT_ENABLED=false"}
    client = get_redis()
    if client is None:
        return {
            "enabled": True,
            "backend": "local",
            "ok": True,
            "detail": f"redis unreachable — process-local limit={settings.rate_limit_chat_per_minute}/min",
        }
    try:
        client.ping()
        return {
            "enabled": True,
            "backend": "redis",
            "ok": True,
            "detail": f"limit={settings.rate_limit_chat_per_minute}/min",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "backend": "local",
            "ok": True,
            "detail": f"redis error — process-local limit={settings.rate_limit_chat_per_minute}/min ({exc})",
        }


def enforce_chat_rate_limit(user: CurrentUser) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    limit = max(1, int(settings.rate_limit_chat_per_minute))
    key = f"rag:ratelimit:chat:{user.tenant_id}:{user.id}"
    n = _incr(key, window_seconds=60)
    if n > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"chat rate limit exceeded: {limit} requests per minute",
        )


def enforce_auth_rate_limit(request: Request, *, identity: str | None = None) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    limit = max(1, int(settings.rate_limit_auth_per_minute))
    ident = (identity or "").strip().lower()
    if not ident:
        host = request.client.host if request.client else "unknown"
        ident = f"ip:{host}"
    key = f"rag:ratelimit:auth:{ident}"
    n = _incr(key, window_seconds=60)
    if n > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"auth rate limit exceeded: {limit} requests per minute",
        )
