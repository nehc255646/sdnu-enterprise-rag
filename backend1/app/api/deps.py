from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token, validate_tenant_id

_bearer = HTTPBearer(auto_error=False)


def require_tenant_header(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id", description="Tenant id (required)")],
) -> str:
    if x_tenant_id is None or not str(x_tenant_id).strip():
        raise HTTPException(status_code=400, detail="X-Tenant-Id header required")
    return str(x_tenant_id).strip()


def require_auth(
    x_tenant_id: Annotated[str, Depends(require_tenant_header)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
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


require_tenant = require_auth
