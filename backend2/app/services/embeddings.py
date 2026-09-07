"""Query embeddings — must match 后端1 ingest model for Qdrant search."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_embeddings():
    settings = get_settings()
    provider = (settings.embedding_provider or "huggingface").lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    # Default: local HuggingFace (no API key needed for smoke)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=settings.embedding_model)
    except Exception as exc:  # noqa: BLE001
        logger.warning("HuggingFace embeddings unavailable (%s); using hash stub", exc)
        return _HashEmbeddings()


class _HashEmbeddings:
    """Deterministic stub for unit tests / offline smoke (dim=384)."""

    dim = 384

    def embed_query(self, text: str) -> list[float]:
        import hashlib
        import struct

        digest = hashlib.sha256(text.encode()).digest()
        vals: list[float] = []
        seed = digest
        while len(vals) < self.dim:
            for i in range(0, len(seed), 4):
                if len(vals) >= self.dim:
                    break
                chunk = seed[i : i + 4]
                if len(chunk) < 4:
                    break
                (n,) = struct.unpack(">I", chunk)
                vals.append((n / 0xFFFFFFFF) * 2 - 1)
            seed = hashlib.sha256(seed).digest()
        # L2 normalize
        norm = sum(v * v for v in vals) ** 0.5 or 1.0
        return [v / norm for v in vals]
