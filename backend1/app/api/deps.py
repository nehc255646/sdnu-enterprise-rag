from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

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
    """Verify Bearer JWT and align tenant_id with X-Tenant-Id.

    Returns tenant_id. Matches 后端2 handoff:
    - missing/invalid token → 401
    - empty tenant header → 400
    - JWT tenant_id mismatch → 403
    """
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
    return x_tenant_id


# backwards-compatible name used by routes
require_tenant = require_auth
