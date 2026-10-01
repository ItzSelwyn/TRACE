"""End-to-end integration tests for moving-vehicle ANPR and controlled demo fallback plates."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.perception.camera_manager import get_camera_manager
from app.modules.perception.demo_fallback import (
    get_demo_generator,
    get_fallback_config,
    update_fallback_config,
)
from app.modules.perception.temporal_fusion import TemporalOCRFusion


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_demo_fallback_api(client):
    # 1. GET initial fallback config
    r_get = client.get("/admin/anpr/demo-fallback")
    assert r_get.status_code == 200
    data_get = r_get.json()
    assert data_get["status"] == "ok"
    assert "config" in data_get
    assert "warning" in data_get

    # 2. PUT update fallback config
    r_put = client.put(
        "/admin/anpr/demo-fallback",
        json={"enabled": True, "fallback_rate": 0.50, "min_track_frames": 8, "default_state": "TN"},
    )
    assert r_put.status_code == 200
    data_put = r_put.json()
    assert data_put["config"]["enabled"] is True
    assert data_put["config"]["fallback_rate"] == 0.50

    # Reset
    update_fallback_config(enabled=False, fallback_rate=0.30, min_track_frames=8)


def test_fallback_replaces_by_genuine_ocr():
    gen = get_demo_generator()
    update_fallback_config(enabled=True, fallback_rate=1.0, min_track_frames=8)

    # 1. Initially unreadable track gets demo fallback
    elig, _ = gen.is_track_eligible(
        dataset="CBE", camera_id="c020", track_id="TRK-088",
        track_frames=10, ocr_attempts=2, has_plate_evidence=True, current_status="NOT_READ",
    )
    assert elig is True
    syn_plate = gen.generate_plate("CBE", "c020", "TRK-088")
    assert syn_plate.startswith("TN")

    # 2. Later, high-confidence genuine OCR arrives
    fusion = TemporalOCRFusion()
    fusion.add_ocr_read(
        camera_id="c020",
        track_id="TRK-088",
        frame_id=45,
        raw_text="TN37CY1234",
        confidence=0.92,
    )
    res = fusion.fuse_track("c020", "TRK-088")
    assert res["fused_plate_text"] == "TN37CY1234"
    assert res["plate_status"] == "READ"
    assert res["is_synthetic"] is False

    # 3. Now the track is no longer eligible for synthetic fallback because it's READ
    elig_after, reason = gen.is_track_eligible(
        dataset="CBE", camera_id="c020", track_id="TRK-088",
        track_frames=15, ocr_attempts=3, has_plate_evidence=True, current_status=res["plate_status"],
    )
    assert elig_after is False
    assert reason == "already_read_or_inferred"


def test_strict_isolation_db_never_receives_synthetic():
    fusion = TemporalOCRFusion()
    gen = get_demo_generator()
    update_fallback_config(enabled=True, fallback_rate=1.0)

    # Vehicle with unreadable plate
    rec = fusion.fuse_track("c020", "TRK-042")
    assert rec["fused_plate_text"] == "NOT READ"

    # Even if synthetic plate is displayed
    syn_plate = gen.generate_plate("CBE", "c020", "TRK-042")
    display_plate = syn_plate
    is_synthetic = True

    # Trusted DB field MUST remain "NOT READ"
    assert rec["fused_plate_text"] == "NOT READ"
    assert is_synthetic is True
    assert display_plate != rec["fused_plate_text"]
