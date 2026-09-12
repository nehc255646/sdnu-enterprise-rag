import uuid

from fastapi.testclient import TestClient


def test_register_invalid_tenant(api_client: TestClient):
    r = api_client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "secret1", "tenant_id": "../tmp"},
    )
    assert r.status_code == 400


def test_login_missing_tenant_and_bad_password(api_client: TestClient):
    email = f"b-{uuid.uuid4().hex[:8]}@example.com"
    r = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1", "tenant_id": "tenant-x"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    bad = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrongpass", "tenant_id": "tenant-x"},
    )
    assert bad.status_code == 401
    me = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 400
    mismatch = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": "other-tenant"},
    )
    assert mismatch.status_code == 403
    ok = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": "tenant-x"},
    )
    assert ok.status_code == 200
    assert ok.json()["email"] == email


def test_password_rejects_over_72_bytes(api_client: TestClient):
    r = api_client.post(
        "/api/v1/auth/register",
        json={"email": "long@example.com", "password": "x" * 73, "tenant_id": "tenant-x"},
    )
    assert r.status_code == 422
