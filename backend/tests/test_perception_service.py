from app.modules.perception import process_all_cameras, process_camera_cycle


def test_process_camera_cycle_reports_down_on_missing_feed():
    result = process_camera_cycle("cam-01", frame_count=0, simulate_failure=True)

    assert result["camera_id"] == "cam-01"
    assert result["camera_status"] == "down"
    assert result["observations"] == []
    assert result["ocr_reads"] == []


def test_process_camera_cycle_returns_fused_observation_for_valid_feed():
    result = process_camera_cycle("cam-02", frame_count=3, simulate_failure=False)

    assert result["camera_id"] == "cam-02"
    assert result["camera_status"] in {"online", "degraded"}
    assert len(result["observations"]) >= 1
    assert all("fused_plate_text" in obs for obs in result["observations"])


def test_process_all_cameras_keeps_running_when_one_camera_fails():
    results = process_all_cameras(
        ["cam-good", "cam-bad"],
        dataset_records={
            "cam-good": [{"vehicle_id": 11, "frame_id": 1}, {"vehicle_id": 11, "frame_id": 2}],
        },
    )

    assert results["cam-good"]["camera_status"] in {"online", "degraded"}
    assert results["cam-bad"]["camera_status"] == "down"
    assert results["cam-bad"]["observations"] == []
