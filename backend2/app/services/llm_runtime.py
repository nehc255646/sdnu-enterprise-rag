"""In-memory LLM config overlay — PUT /llm/config hot-swaps without restart."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.core.config import get_settings


@dataclass
class LLMRuntimeConfig:
    base_url: str
    api_key: str | None
    model: str


_lock = Lock()
_override: LLMRuntimeConfig | None = None


def get_llm_config() -> LLMRuntimeConfig:
    settings = get_settings()
    with _lock:
        if _override is not None:
            return LLMRuntimeConfig(
                base_url=_override.base_url,
                api_key=_override.api_key,
                model=_override.model,
            )
    return LLMRuntimeConfig(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


def set_llm_config(*, base_url: str, model: str, api_key: str | None = None) -> LLMRuntimeConfig:
    """Update runtime LLM settings. Empty api_key keeps previous / falls back to env."""
    current = get_llm_config()
    key = api_key if api_key is not None else current.api_key
    # allow explicit clear with empty string → treat as None (sk-no-auth path)
    if api_key is not None and api_key.strip() == "":
        key = None
    cfg = LLMRuntimeConfig(
        base_url=(base_url or current.base_url).rstrip("/"),
        api_key=key,
        model=(model or current.model).strip(),
    )
    if not cfg.model:
        raise ValueError("model required")
    if not cfg.base_url:
        raise ValueError("base_url required")
    with _lock:
        global _override
        _override = cfg
    return cfg


def effective_api_key(cfg: LLMRuntimeConfig | None = None) -> str:
    c = cfg or get_llm_config()
    key = (c.api_key or "").strip()
    return key if key else "sk-no-auth"
