"""Per-tenant in-memory LLM config overlay."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlparse

from app.core.config import get_settings

_ALLOWED_LLM_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "host.docker.internal"})
_BLOCKED_LLM_HOSTS = frozenset(
    {
        "postgres",
        "redis",
        "qdrant",
        "backend",
        "frontend",
        "metadata.google.internal",
        "metadata.google.com",
        "169.254.169.254",
    }
)


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
        base_url=settings.openai_base_url.rstrip("/"),
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


def _host_blocked(host: str) -> bool:
    host = host.strip().lower().rstrip(".")
    if host in _ALLOWED_LLM_HOSTS:
        return False
    if host in _BLOCKED_LLM_HOSTS:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    if addr.is_loopback:
        return False
    return bool(
        addr.is_private
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_llm_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be http(s) with a host")
    host = parsed.hostname or ""
    if not host or _host_blocked(host):
        raise ValueError("base_url host is not allowed")
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
    env = _env_config()
    current = get_llm_config(tenant_id)
    raw_url = (base_url or current.base_url).strip()
    new_url = validate_llm_base_url(raw_url)
    new_model = (model or current.model).strip()
    if not new_model:
        raise ValueError("model required")

    if api_key is not None and api_key.strip() == "":
        key = None
    elif api_key is not None:
        key = api_key
    else:
        key = current.api_key
        env_key = (env.api_key or "").strip()
        if new_url != current.base_url and (key or "").strip() == env_key:
            key = None

    cfg = LLMRuntimeConfig(base_url=new_url, api_key=key, model=new_model)
    with _lock:
        _overrides[tenant_id] = cfg
    return cfg


def clear_llm_overrides() -> None:
    with _lock:
        _overrides.clear()


def effective_api_key(cfg: LLMRuntimeConfig | None = None) -> str:
    c = cfg or get_llm_config()
    key = (c.api_key or "").strip()
    return key if key else "sk-no-auth"
