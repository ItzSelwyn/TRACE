import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import create_access_token


def test_perception_status_route_is_available():
    client = TestClient(app)
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "operator"})
    response = client.get("/perception/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "cameras" in payload
    assert set(payload["cameras"]) == {"c020", "c023", "c029", "c035"}
