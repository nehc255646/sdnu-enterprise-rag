"""Redis list queue for async ingest jobs; falls back to in-process when Redis down."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.cache import get_redis
from app.core.config import get_settings

logger = logging.getLogger(__name__)
_memory_queue: list[dict[str, Any]] = []


def enqueue_ingest(job: dict[str, Any]) -> None:
    settings = get_settings()
    client = get_redis()
    payload = json.dumps(job)
    if client is None:
        _memory_queue.append(job)
        return
    client.rpush(settings.ingest_queue_key, payload)


def dequeue_ingest(timeout: int = 2) -> dict[str, Any] | None:
    settings = get_settings()
    client = get_redis()
    if client is None:
        if not _memory_queue:
            return None
        return _memory_queue.pop(0)
    item = client.blpop(settings.ingest_queue_key, timeout=timeout)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)
