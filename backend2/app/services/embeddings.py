"""Swappable embedding backend: openai | huggingface | ollama | hash.

Aligned with 后端1 so query vectors match ingested chunks (qwen3-embedding:0.6b / 1024-dim).
"""

from __future__ import annotations

from functools import lru_cache

import httpx
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
        for ch in text:
            o = ord(ch)
            if o > 127:
                vec[o % self.dims] += 0.15
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


class OllamaEmbeddings(Embeddings):
    """Ollama native /api/embed (OpenAI-compatible /v1/embeddings also works via openai provider)."""

    def __init__(self, *, model: str, base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _embed(self, texts: list[str]) -> list[list[float]]:
        # Prefer /api/embed (batch); fall back to /api/embeddings per text
        url = f"{self.base_url}/api/embed"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, json={"model": self.model, "input": texts})
                if r.status_code == 404:
                    raise httpx.HTTPStatusError("not found", request=r.request, response=r)
                r.raise_for_status()
                data = r.json()
                embs = data.get("embeddings")
                if not embs:
                    raise RuntimeError(f"ollama embed empty response: {data}")
                return embs
        except httpx.HTTPStatusError:
            out: list[list[float]] = []
            with httpx.Client(timeout=self.timeout) as client:
                for t in texts:
                    r = client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model, "prompt": t},
                    )
                    r.raise_for_status()
                    out.append(r.json()["embedding"])
            return out

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


def build_embeddings(settings: Settings | None = None) -> Embeddings:
    settings = settings or get_settings()
    provider = settings.embedding_provider.lower()
    if provider == "hash":
        return HashEmbeddings()
    if provider == "ollama":
        return OllamaEmbeddings(
            model=settings.ollama_embedding_model or settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        kwargs: dict = {"model": settings.openai_embedding_model}
        api_key = settings.openai_api_key or "sk-no-auth"
        kwargs["api_key"] = api_key
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return OpenAIEmbeddings(**kwargs)

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=settings.embedding_model)

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}")


@lru_cache
def get_embeddings() -> Embeddings:
    return build_embeddings()
