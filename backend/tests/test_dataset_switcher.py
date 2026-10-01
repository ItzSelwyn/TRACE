"""Tests for Global Dataset Switcher (S04, S05, CBE)."""

import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.modules.perception.camera_manager import get_camera_manager
from app.modules.perception.dataset_profiles import (
    DATASET_PROFILES,
    _get_active_dataset_path,
    get_active_dataset_key,
    get_dataset_profile,
    validate_dataset_footage,
)

client = TestClient(app)


def test_footage_directory_validation():
    """Verify all 4 camera footage files exist for S04, S05, and CBE."""
    for key in ["S04", "S05", "CBE"]:
        sources = validate_dataset_footage(key)
        assert len(sources) == 4, f"Expected 4 cameras for {key}, got {len(sources)}"
        assert set(sources.keys()) == {"c020", "c023", "c028", "c029"}
        for cam_id, rel_path in sources.items():
            full_path = Path("data") / rel_path
            assert full_path.exists(), f"Footage missing: {full_path}"


def test_get_dataset_profiles():
    """Verify profile metadata for CityFlow and Coimbatore."""
    s04 = get_dataset_profile("S04")
    assert s04["map_profile"] == "cityflow"
    assert s04["label"] == "CityFlow S04"

    s05 = get_dataset_profile("S05")
    assert s05["map_profile"] == "cityflow"
    assert s05["label"] == "CityFlow S05"

    cbe = get_dataset_profile("CBE")
    assert cbe["map_profile"] == "coimbatore"
    assert cbe["label"] == "Coimbatore CBE"
    assert cbe["cameras"]["c020"]["latitude"] > 10.0
    assert cbe["cameras"]["c020"]["longitude"] > 76.0


def test_admin_get_dataset_endpoint():
    """Verify GET /admin/dataset returns current active dataset and options."""
    res = client.get("/admin/dataset")
    assert res.status_code == 200
    payload = res.json()
    assert "active_dataset" in payload
    assert "map_profile" in payload
    assert "available_datasets" in payload
    ids = [d["id"] for d in payload["available_datasets"]]
    assert "S04" in ids
    assert "S05" in ids
    assert "CBE" in ids


def test_admin_put_invalid_dataset():
    """Verify switching to an invalid dataset is rejected with 400 and does not change active dataset."""
    initial_res = client.get("/admin/dataset")
    initial_dataset = initial_res.json()["active_dataset"]

    res = client.put("/admin/dataset", json={"dataset": "NON_EXISTENT_DATASET"})
    assert res.status_code == 400

    after_res = client.get("/admin/dataset")
    assert after_res.json()["active_dataset"] == initial_dataset


def test_admin_switch_dataset_lifecycle():
    """Verify switching S04 -> CBE -> S05 updates active dataset, map profile, and camera configs."""
    mgr = get_camera_manager()
    initial_gen = mgr.dataset_generation

    # 1. Switch to S04
    res = client.put("/admin/dataset", json={"dataset": "S04"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["active_dataset"] == "S04"
    assert payload["map_profile"] == "cityflow"
    assert mgr.dataset_generation > initial_gen

    gen_s04 = mgr.dataset_generation
    cams = {c["camera_id"]: c for c in mgr.list_cameras()}
    assert "S04" in cams["c020"]["source_path"]

    # 2. Switch to CBE
    res = client.put("/admin/dataset", json={"dataset": "CBE"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["active_dataset"] == "CBE"
    assert payload["map_profile"] == "coimbatore"
    assert mgr.dataset_generation > gen_s04

    gen_cbe = mgr.dataset_generation
    cams = {c["camera_id"]: c for c in mgr.list_cameras()}
    assert "CBE" in cams["c020"]["source_path"]
    # Check Coimbatore coordinates (around Kuniyamuthur lat ~10.94, lng ~76.95)
    assert abs(cams["c020"]["latitude"] - 10.9472) < 0.01
    assert abs(cams["c020"]["longitude"] - 76.9538) < 0.01

    # 3. Switch to S05
    res = client.put("/admin/dataset", json={"dataset": "S05"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["active_dataset"] == "S05"
    assert payload["map_profile"] == "cityflow"
    assert mgr.dataset_generation > gen_cbe

    cams = {c["camera_id"]: c for c in mgr.list_cameras()}
    assert "S05" in cams["c020"]["source_path"]
    # Check CityFlow coordinates restored
    assert abs(cams["c020"]["latitude"] - 42.4991) < 0.01

    # 4. Check active_dataset.json persistence
    persisted_file = _get_active_dataset_path()
    assert persisted_file.exists()
    with open(persisted_file, "r") as f:
        data = json.load(f)
    assert data.get("active_dataset") == "S05"
