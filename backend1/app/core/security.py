"""JWT verification (HS256)."""

from __future__ import annotations

from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid or expired token") from exc
