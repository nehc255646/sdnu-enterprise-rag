"""Redis list queue for async ingest jobs."""

from __future__ import annotations

import json
from typing import Any

from app.core.cache import get_redis
from app.core.config import get_settings


def enqueue_ingest(job: dict[str, Any]) -> None:
    settings = get_settings()
    client = get_redis()
    if client is None:
        raise RuntimeError("ingest worker requires Redis")
    client.rpush(settings.ingest_queue_key, json.dumps(job))


def dequeue_ingest(timeout: int = 2) -> dict[str, Any] | None:
    settings = get_settings()
    client = get_redis()
    if client is None:
        return None
    item = client.blpop(settings.ingest_queue_key, timeout=timeout)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)
