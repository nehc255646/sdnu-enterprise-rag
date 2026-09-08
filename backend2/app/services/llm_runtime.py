"""Per-tenant in-memory LLM config overlay."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlparse

from app.core.config import get_settings


@dataclass
class LLMRuntimeConfig:
    base_url: str
    api_key: str | None
    model: str


_lock = Lock()
_overrides: dict[str, LLMRuntimeConfig] = {}


def _env_config() -> LLMRuntimeConfig:
    settings = get_settings()
    return LLMRuntimeConfig(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


def allowed_llm_hosts() -> set[str]:
    settings = get_settings()
    hosts = {"127.0.0.1", "localhost", "host.docker.internal", "::1"}
    env_host = urlparse(settings.openai_base_url).hostname
    if env_host:
        hosts.add(env_host.lower())
    for item in settings.llm_base_url_allowlist.split(","):
        h = item.strip().lower()
        if h:
            hosts.add(h)
    return hosts


def validate_llm_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be http(s) with a host")
    host = (parsed.hostname or "").lower()
    if host not in allowed_llm_hosts():
        raise ValueError(f"base_url host not allowed: {host}")
    return url.rstrip("/")


def get_llm_config(tenant_id: str | None = None) -> LLMRuntimeConfig:
    env = _env_config()
    if not tenant_id:
        return env
    with _lock:
        override = _overrides.get(tenant_id)
        if override is None:
            return env
        return LLMRuntimeConfig(
            base_url=override.base_url,
            api_key=override.api_key,
            model=override.model,
        )


def set_llm_config(
    *,
    tenant_id: str,
    base_url: str,
    model: str,
    api_key: str | None = None,
) -> LLMRuntimeConfig:
    if not tenant_id:
        raise ValueError("tenant_id required")
    current = get_llm_config(tenant_id)
    key = api_key if api_key is not None else current.api_key
    if api_key is not None and api_key.strip() == "":
        key = None
    raw_url = (base_url or current.base_url).strip()
    cfg = LLMRuntimeConfig(
        base_url=validate_llm_base_url(raw_url),
        api_key=key,
        model=(model or current.model).strip(),
    )
    if not cfg.model:
        raise ValueError("model required")
    with _lock:
        _overrides[tenant_id] = cfg
    return cfg


def effective_api_key(cfg: LLMRuntimeConfig | None = None) -> str:
    c = cfg or get_llm_config()
    key = (c.api_key or "").strip()
    return key if key else "sk-no-auth"
