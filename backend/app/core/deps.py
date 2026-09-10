"""Auth dependencies: tenant JWT (ingest) and current user (chat)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token, validate_tenant_id

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    email: str
    tenant_id: str


def require_tenant_header(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id", description="Tenant id (required)")],
) -> str:
    if x_tenant_id is None or not str(x_tenant_id).strip():
        raise HTTPException(status_code=400, detail="X-Tenant-Id header required")
    return str(x_tenant_id).strip()


def require_tenant(
    x_tenant_id: Annotated[str, Depends(require_tenant_header)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """JWT + matching X-Tenant-Id. User row is not required (tenant-scoped ingest)."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Authorization Bearer token required")
    try:
        payload = decode_access_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid or expired token") from None

    token_tenant = payload.get("tenant_id")
    if not token_tenant:
        raise HTTPException(status_code=401, detail="token missing tenant_id claim")
    if str(token_tenant) != x_tenant_id:
        raise HTTPException(status_code=403, detail="X-Tenant-Id does not match token tenant_id")
    try:
        return validate_tenant_id(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid tenant_id") from None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
) -> CurrentUser:
    """JWT + matching tenant + existing users row (chat / sessions / llm)."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token missing sub/tenant_id")

    if not x_tenant_id or not str(x_tenant_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header required",
        )
    if x_tenant_id.strip() != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Tenant-Id does not match token tenant",
        )
    try:
        validate_tenant_id(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid tenant_id") from None

    from app.models import User

    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found for tenant")

    return CurrentUser(id=user.id, email=user.email, tenant_id=user.tenant_id)
