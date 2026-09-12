import pytest

from app.chat.llm_runtime import (
    clear_llm_overrides,
    effective_api_key,
    set_llm_config,
    validate_llm_base_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://postgres:5432",
        "http://redis:6379",
        "http://qdrant:6333",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1:80",
        "http://192.168.1.1",
        "ftp://example.com",
        "http://not-a-host",
    ],
)
def test_blocks_private_llm_url(url: str):
    with pytest.raises(ValueError):
        validate_llm_base_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434/v1",
        "http://localhost:11434/v1",
        "http://host.docker.internal:11434/v1",
        "https://api.openai.com/v1",
    ],
)
def test_allows_demo_llm_url(url: str):
    assert validate_llm_base_url(url) == url.rstrip("/")


def test_url_change_drops_env_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    clear_llm_overrides()
    try:
        same = set_llm_config(
            tenant_id="t1",
            base_url="http://127.0.0.1:11434/v1",
            model="qwen2.5:1.5b",
        )
        assert same.api_key == "sk-env-secret"
        changed = set_llm_config(
            tenant_id="t1",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        assert changed.api_key is None
        assert effective_api_key(changed) == "sk-no-auth"
    finally:
        get_settings.cache_clear()
        clear_llm_overrides()
