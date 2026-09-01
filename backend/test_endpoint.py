"""Test the perception endpoint."""
from fastapi.testclient import TestClient
from app.main import app


def test_perception_status():
    client = TestClient(app)
    response = client.get("/perception/status")
    data = response.json()
    print("Status code:", response.status_code)
    print("Status:", data.get("status"))
    print("Source:", data.get("source"))
    print("Cameras count:", data.get("camera_count"))
    print("Loaded cameras:", data.get("_debug", {}).get("loaded_cameras"))
    print("Record counts:", data.get("_debug", {}).get("dataset_records_counts"))
    return data


if __name__ == "__main__":
    test_perception_status()