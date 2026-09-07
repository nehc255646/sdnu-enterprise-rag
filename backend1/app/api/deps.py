from typing import Annotated

from fastapi import Header, HTTPException


def require_tenant(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id", description="Tenant id (required)")],
) -> str:
    """Auth placeholder for 后端2 — require tenant header for isolation.

    OpenAPI marks X-Tenant-Id as required. JWT verification will be wired by 后端2.
    """
    if not x_tenant_id or not x_tenant_id.strip():
        raise HTTPException(status_code=401, detail="X-Tenant-Id header required")
    return x_tenant_id.strip()
