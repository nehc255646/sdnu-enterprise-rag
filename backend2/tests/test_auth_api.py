import uuid

from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_register_invalid_tenant():
    with _client() as c:
        r = c.post(
            "/api/v1/auth/register",
            json={"email": "a@example.com", "password": "secret1", "tenant_id": "../tmp"},
        )
        assert r.status_code == 400


def test_login_missing_tenant_and_bad_password():
    with _client() as c:
        email = f"b-{uuid.uuid4().hex[:8]}@example.com"
        r = c.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "secret1", "tenant_id": "tenant-x"},
        )
        assert r.status_code == 201
        token = r.json()["access_token"]
        bad = c.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrongpass", "tenant_id": "tenant-x"},
        )
        assert bad.status_code == 401
        me = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code in (400, 422)
        mismatch = c.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": "other-tenant"},
        )
        assert mismatch.status_code == 403
        ok = c.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": "tenant-x"},
        )
        assert ok.status_code == 200
        assert ok.json()["email"] == email
