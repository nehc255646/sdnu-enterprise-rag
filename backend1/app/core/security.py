"""JWT verification (HS256) and tenant_id format checks."""

from __future__ import annotations

import re
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings

TENANT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
PLACEHOLDER_JWT_SECRETS = frozenset(
    {
        "change-me-to-a-long-random-string",
        "change-me-in-prod",
        "dev-shared-secret-change-me",
    }
)


def validate_tenant_id(value: str) -> str:
    tenant_id = (value or "").strip()
    if not TENANT_ID_RE.fullmatch(tenant_id):
        raise ValueError("invalid tenant_id")
    return tenant_id


def assert_jwt_secret() -> None:
    settings = get_settings()
    secret = (settings.jwt_secret or "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET is required")
    env = (settings.app_env or "development").lower()
    if secret in PLACEHOLDER_JWT_SECRETS and env not in {"development", "dev", "test"}:
        raise RuntimeError("JWT_SECRET is a placeholder; set a unique secret")


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid or expired token") from exc
    if not payload.get("sub") or not payload.get("tenant_id"):
        raise ValueError("token missing sub/tenant_id")
    return payload
