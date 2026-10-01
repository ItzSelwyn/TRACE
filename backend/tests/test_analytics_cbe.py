import uuid
import pytest
from fastapi.testclient import TestClient

from app.dependencies import create_access_token
from app.main import app

def test_analytics_heatmap_and_od_matrix_cbe():
    client = TestClient(app)
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # Test CBE Heatmap
    res_cbe = client.get("/analytics/heatmap?dataset=CBE", headers=headers)
    assert res_cbe.status_code == 200
    data_cbe = res_cbe.json()
    assert "Palghat" in data_cbe["corridor_name"]
    assert "CBE" in data_cbe["corridor_name"]
    assert "Palghat Rd North (C020)" in data_cbe["cameras_label"]
    assert len(data_cbe["camera_stats"]) == 4
    
    # Verify camera coordinates match revised CBE locations
    cam_map = {c["alias"] if "alias" in c else c["name"]: c for c in data_cbe["camera_stats"]}
    # Check c020: 76.951820, 10.939350
    c020 = next((c for c in data_cbe["camera_stats"] if "020" in c["name"]), None)
    assert c020 is not None
    assert abs(c020["longitude"] - 76.951820) < 0.001
    assert abs(c020["latitude"] - 10.939350) < 0.001

    # Check c029: 76.948940, 10.937430
    c029 = next((c for c in data_cbe["camera_stats"] if "029" in c["name"]), None)
    assert c029 is not None
    assert abs(c029["longitude"] - 76.948940) < 0.001
    assert abs(c029["latitude"] - 10.937430) < 0.001

    # Verify road segments
    assert len(data_cbe["segments"]) == 3
    seg_names = [s["name"] for s in data_cbe["segments"]]
    assert any("Palghat Rd" in n for n in seg_names)
    assert any("Kovaipudur Rd" in n for n in seg_names)

    # Test CBE OD Matrix
    res_od = client.get("/analytics/od-matrix?dataset=CBE", headers=headers)
    assert res_od.status_code == 200
    od_data = res_od.json()
    assert "Palghat" in od_data["corridor_name"]
    assert od_data["zones"] == [
        "CAM-020 (Palghat Rd N)",
        "CAM-023 (Junction)",
        "CAM-028 (Palghat Rd S)",
        "CAM-029 (Kovaipudur Rd)",
    ]

    # Test CityFlow S05 remains intact
    res_s05 = client.get("/analytics/heatmap?dataset=S05", headers=headers)
    assert res_s05.status_code == 200
    data_s05 = res_s05.json()
    assert "University Ave" in data_s05["corridor_name"]
    c020_s05 = next((c for c in data_s05["camera_stats"] if "020" in c["name"]), None)
    assert c020_s05 is not None
    assert abs(c020_s05["longitude"] - (-90.675620)) < 0.001
