"""Tests for Admin Camera Input, Playback, and Perception Scenario Control."""

import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.modules.perception.source_discovery import discover_sources, load_cityflow_sync_metadata
from app.modules.perception.camera_manager import get_camera_manager

client = TestClient(app)


def test_discover_sources():
    """Verify source discovery scans data/ and identifies videos, images, and CityFlow metadata."""
    sources = discover_sources()
    assert "videos" in sources
    assert "images" in sources
    assert "scenarios" in sources

    # Check that CityFlow S04 cameras are discovered
    vpaths = [v["path"] for v in sources["videos"]]
    assert any("c020" in p for p in vpaths)
    assert any("c023" in p for p in vpaths)
    assert any("c029" in p for p in vpaths)
    assert any("c035" in p for p in vpaths)

    # Check images discovered
    assert len(sources["images"]) > 0


def test_cityflow_sync_metadata():
    """Verify S04 timestamp and framenum offsets match dataset ground truth."""
    sync_meta = load_cityflow_sync_metadata()
    assert "S04" in sync_meta
    s04 = sync_meta["S04"]
    assert "c020" in s04
    assert s04["c020"]["start_timestamp_s"] == 25.905
    assert s04["c023"]["start_timestamp_s"] == 45.716
    assert s04["c029"]["start_timestamp_s"] == 125.788
    assert s04["c035"]["start_timestamp_s"] == 165.568


def test_admin_list_cameras():
    """Verify GET /admin/cameras returns all 4 cameras."""
    res = client.get("/admin/cameras")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"
    assert payload["count"] == 4
    cams = {c["camera_id"]: c for c in payload["cameras"]}
    assert "c020" in cams
    assert "c023" in cams
    assert "c029" in cams
    assert "c035" in cams
    assert cams["c020"]["sync_offset_s"] == 25.905


def test_admin_get_sources():
    """Verify GET /admin/sources endpoint."""
    res = client.get("/admin/sources")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"
    data = payload["data"]
    assert len(data["videos"]) >= 4


def test_admin_playback_status_and_control():
    """Verify playback status and settings update."""
    res = client.get("/admin/playback/status")
    assert res.status_code == 200
    status = res.json()
    assert "sync_mode" in status
    assert "playback_state" in status

    # Change playback speed and pause
    res = client.patch(
        "/admin/playback/settings",
        json={"playback_speed": 2.0, "playback_state": "paused", "sync_mode": "independent"},
    )
    assert res.status_code == 200
    updated = res.json()["playback"]
    assert updated["playback_speed"] == 2.0
    assert updated["playback_state"] == "paused"
    assert updated["sync_mode"] == "independent"

    # Restore to synchronized and playing
    res = client.patch(
        "/admin/playback/settings",
        json={"playback_speed": 1.0, "playback_state": "playing", "sync_mode": "synchronized"},
    )
    assert res.status_code == 200
    assert res.json()["playback"]["sync_mode"] == "synchronized"


def test_admin_camera_enable_disable():
    """Verify enabling and disabling a camera."""
    res = client.post("/admin/cameras/c020/disable")
    assert res.status_code == 200
    cam = res.json()["camera"]
    assert cam["enabled"] is False
    assert cam["status"] == "DISABLED"

    res = client.post("/admin/cameras/c020/enable")
    assert res.status_code == 200
    cam = res.json()["camera"]
    assert cam["enabled"] is True


def test_admin_camera_source_hot_swap():
    """Verify hot-swapping a camera source to an image and back to video."""
    sources = discover_sources()
    assert len(sources["images"]) > 0
    img_path = sources["images"][0]["path"]

    # Swap c035 to image
    res = client.patch(
        "/admin/cameras/c035/source",
        json={"source_path": img_path, "source_type": "image"},
    )
    assert res.status_code == 200
    cam = res.json()["camera"]
    assert cam["source_type"] == "image"
    assert cam["source_path"] == img_path

    # Swap back to video
    res = client.patch(
        "/admin/cameras/c035/source",
        json={"source_path": "footage/c035/vdo.avi", "source_type": "video"},
    )
    assert res.status_code == 200
    cam = res.json()["camera"]
    assert cam["source_type"] == "video"


def test_admin_camera_preview():
    """Verify GET /admin/cameras/{id}/preview returns metadata and preview base64."""
    res = client.get("/admin/cameras/c020/preview")
    assert res.status_code == 200
    payload = res.json()
    assert payload["camera_id"] == "c020"
    assert "preview_b64" in payload
    assert "status" in payload


def test_admin_debug_test_image():
    """Verify POST /admin/debug/test-image processes an image through perception."""
    sources = discover_sources()
    if sources["images"]:
        test_img = sources["images"][0]["path"]
        res = client.post("/admin/debug/test-image", json={"image_path": test_img})
        assert res.status_code == 200
        payload = res.json()
        assert payload["status"] == "ok"
        result = payload["result"]
        assert "vehicle_colour" in result
        assert "original_image_b64" in result
        assert "vehicle_crop_b64" in result
        assert "plate_crop_b64" in result

