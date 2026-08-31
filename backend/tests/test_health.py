import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.config import settings
from app.dependencies import create_access_token
from app.main import app
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def test_password_hash_round_trip_works_with_project_bcrypt_version():
    hashed = pwd_context.hash("trace123")
    assert pwd_context.verify("trace123", hashed) is True


@pytest.mark.anyio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


def test_m1_route_scaffolds_return_placeholder_responses():
    client = TestClient(app)
    segment_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/analytics/heatmap", headers=headers).status_code == 200
    assert client.get("/analytics/od-matrix", headers=headers).status_code == 200
    assert client.get(f"/analytics/segments/{segment_id}", headers=headers).status_code == 200
    assert client.get(f"/analytics/forecast/{segment_id}", headers=headers).status_code == 200
    assert client.get("/alerts", headers=headers).status_code == 200
    assert client.patch(f"/alerts/{alert_id}", json={"reviewed": True}, headers=headers).status_code == 200
    assert client.get("/blacklist", headers=headers).status_code == 200
    assert client.post("/blacklist", json={"plate_text": "ABC123", "reason": "Test"}, headers=headers).status_code == 201


@pytest.mark.anyio
async def test_seeded_users_can_login_and_receive_jwt():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            data={"username": "admin@trace.local", "password": "trace123"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert isinstance(payload["access_token"], str)
    assert len(payload["access_token"].split(".")) == 3


@pytest.mark.anyio
async def test_admin_can_access_protected_route_but_operator_cannot():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = create_access_token({"sub": str(uuid.uuid4()), "role": "admin"})
        operator_token = create_access_token({"sub": str(uuid.uuid4()), "role": "operator"})

        admin_get_response = await client.get(
            "/blacklist",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        operator_get_response = await client.get(
            "/blacklist",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        operator_post_response = await client.post(
            "/blacklist",
            json={"plate_text": "ABC123", "reason": "Test"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )

    assert admin_get_response.status_code == 200
    assert operator_get_response.status_code == 200
    assert operator_post_response.status_code == 403


def test_jwt_generation_uses_configured_secret():
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "admin"})
    assert isinstance(token, str)
    assert len(token.split(".")) == 3
    assert settings.JWT_SECRET == "changeme"
