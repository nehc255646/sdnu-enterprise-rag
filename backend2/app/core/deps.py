"""FastAPI dependencies: current user + mandatory tenant_id."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    email: str
    tenant_id: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
) -> CurrentUser:
    """Require Bearer JWT; tenant_id comes from token (header must match).

    OpenAPI marks X-Tenant-Id as required (no default). Runtime:
    - empty / whitespace-only header → 400
    - header != JWT tenant_id → 403
    Missing header is rejected by FastAPI as required (422) before this body runs.
    """
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

    # Required on protected routes (aligns with 后端1); must match JWT tenant_id
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

    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found for tenant")

    return CurrentUser(id=user.id, email=user.email, tenant_id=user.tenant_id)


def require_tenant_id(user: CurrentUser = Depends(get_current_user)) -> str:
    """Every authenticated request carries tenant_id from JWT."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="tenant_id required")
    return user.tenant_id
