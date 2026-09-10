"""JWT create/verify, password hashing, tenant_id checks."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

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


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    *,
    subject: str,
    tenant_id: str,
    extra: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid or expired token") from exc
    if not payload.get("sub") or not payload.get("tenant_id"):
        raise ValueError("token missing sub/tenant_id")
    return payload
