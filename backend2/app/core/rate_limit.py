"""Chat rate limiting via Redis INCR; degrade = allow when Redis down."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.deps import CurrentUser
from app.services.cache import get_redis, rate_limit_incr

logger = logging.getLogger(__name__)


def rate_limit_status() -> dict:
    """Health-facing snapshot: enabled + backend=redis|disabled."""
    settings = get_settings()
    enabled = bool(settings.rate_limit_enabled)
    if not enabled:
        return {"enabled": False, "backend": "disabled", "ok": True, "detail": "RATE_LIMIT_ENABLED=false"}
    client = get_redis()
    if client is None:
        return {
            "enabled": True,
            "backend": "disabled",
            "ok": False,
            "detail": "optional: redis unreachable — rate limit degraded (allow)",
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
            "backend": "disabled",
            "ok": False,
            "detail": f"optional: redis error — rate limit degraded (allow): {exc}",
        }


def enforce_chat_rate_limit(user: CurrentUser) -> None:
    """Increment Redis counter for user; raise 429 when over limit.

    When rate limiting is disabled or Redis is unreachable, allow the request
    (do not 500).
    """
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    limit = max(1, int(settings.rate_limit_chat_per_minute))
    key = f"rag:ratelimit:chat:{user.tenant_id}:{user.id}"
    try:
        n = rate_limit_incr(key, window_seconds=60)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate limit check failed, allowing: %s", exc)
        return
    # rate_limit_incr returns 0 when Redis unavailable → degrade allow
    if n == 0:
        return
    if n > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"chat rate limit exceeded: {limit} requests per minute",
        )
