"""Swappable embedding backend: openai | huggingface | hash (offline demo)."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.core.config import Settings, get_settings


class HashEmbeddings(Embeddings):
    """Deterministic bag-of-bytes vectors for offline smoke / demo without model download."""

    def __init__(self, dims: int = 64):
        self.dims = dims

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        vec = [0.0] * self.dims
        data = text.encode("utf-8")
        for i, b in enumerate(data):
            vec[i % self.dims] += ((b % 31) + 1) / 31.0
            vec[(i * 7) % self.dims] += ((b % 17) + 1) / 17.0
        # light unigram boost for CJK chars
        for ch in text:
            o = ord(ch)
            if o > 127:
                vec[o % self.dims] += 0.15
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


def build_embeddings(settings: Settings | None = None) -> Embeddings:
    settings = settings or get_settings()
    provider = settings.embedding_provider.lower()
    if provider == "hash":
        return HashEmbeddings()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        kwargs: dict = {"model": settings.openai_embedding_model}
        if settings.openai_api_key:
            kwargs["api_key"] = settings.openai_api_key
        if settings.openai_api_base:
            kwargs["base_url"] = settings.openai_api_base
        return OpenAIEmbeddings(**kwargs)

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=settings.embedding_model)

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}")


@lru_cache
def get_embeddings() -> Embeddings:
    return build_embeddings()
