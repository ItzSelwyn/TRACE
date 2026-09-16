"""Unit tests for controlled synthetic demo fallback plates and strict data isolation."""

import pytest

from app.modules.perception.demo_fallback import (
    DeterministicDemoPlateGenerator,
    get_demo_generator,
    get_fallback_config,
    update_fallback_config,
)
from app.modules.perception.temporal_fusion import TemporalOCRFusion


def test_deterministic_generation_stability():
    gen = DeterministicDemoPlateGenerator()

    # Same track ID must generate identical plate across multiple calls
    plate1 = gen.generate_plate(dataset="CBE", camera_id="c020", track_id="TRK-001")
    plate2 = gen.generate_plate(dataset="CBE", camera_id="c020", track_id="TRK-001")
    plate3 = gen.generate_plate(dataset="CBE", camera_id="c020", track_id="TRK-001")

    assert plate1 == plate2 == plate3
    assert plate1.startswith("TN")  # CBE default prefix

    # Different track ID produces distinct plate (no hardcoded single plate)
    plate_other = gen.generate_plate(dataset="CBE", camera_id="c020", track_id="TRK-002")
    assert plate1 != plate_other


def test_partial_ocr_filling():
    gen = DeterministicDemoPlateGenerator()

    # Partial OCR evidence preserved
    partial = "TN38A"
    res = gen.generate_plate(dataset="CBE", camera_id="c020", track_id="TRK-005", partial_text=partial)
    assert res.startswith("TN")
    assert len(res) >= 9


def test_demo_fallback_eligibility_rules():
    gen = DeterministicDemoPlateGenerator()

    # 1. Disabled by default
    update_fallback_config(enabled=False, fallback_rate=0.30, min_track_frames=8)
    eligible, reason = gen.is_track_eligible(
        dataset="CBE", camera_id="c020", track_id="TRK-010",
        track_frames=12, ocr_attempts=3, has_plate_evidence=True, current_status="NOT_READ",
    )
    assert eligible is False
    assert reason == "demo_fallback_disabled"

    # 2. Enabled but track too young
    update_fallback_config(enabled=True, fallback_rate=0.30, min_track_frames=8)
    eligible_young, reason_young = gen.is_track_eligible(
        dataset="CBE", camera_id="c020", track_id="TRK-010",
        track_frames=4, ocr_attempts=1, has_plate_evidence=True, current_status="NOT_READ",
    )
    assert eligible_young is False
    assert "track_too_young" in reason_young

    # 3. No plate evidence
    eligible_no_ev, reason_no_ev = gen.is_track_eligible(
        dataset="CBE", camera_id="c020", track_id="TRK-010",
        track_frames=15, ocr_attempts=4, has_plate_evidence=False, current_status="NOT_READ",
    )
    assert eligible_no_ev is False
    assert reason_no_ev == "no_plate_evidence"

    # 4. Already read with high confidence genuine OCR
    eligible_read, reason_read = gen.is_track_eligible(
        dataset="CBE", camera_id="c020", track_id="TRK-010",
        track_frames=15, ocr_attempts=4, has_plate_evidence=True, current_status="READ",
    )
    assert eligible_read is False
    assert reason_read == "already_read_or_inferred"


def test_rate_limiting_distribution():
    gen = DeterministicDemoPlateGenerator()
    update_fallback_config(enabled=True, fallback_rate=0.30, min_track_frames=8)

    # Across 100 random tracks, approximately ~30% should be eligible
    eligible_count = 0
    total = 100

    for i in range(total):
        tid = f"TRK-{i:03d}"
        elig, _ = gen.is_track_eligible(
            dataset="CBE", camera_id="c020", track_id=tid,
            track_frames=15, ocr_attempts=4, has_plate_evidence=True, current_status="NOT_READ",
        )
        if elig:
            eligible_count += 1

    # Ratio should be close to 30% (e.g. between 18% and 42%)
    assert 18 <= eligible_count <= 42


def test_dataset_clearing():
    gen = DeterministicDemoPlateGenerator()
    gen.generate_plate(dataset="CBE", camera_id="c020", track_id="TRK-001")
    assert len(gen._cache) > 0

    gen.clear_dataset()
    assert len(gen._cache) == 0


def test_isolation_in_temporal_fusion():
    fusion = TemporalOCRFusion()
    # Unread track
    rec = fusion.fuse_track("c020", "TRK-099")
    # Fused plate text MUST be "NOT READ"
    assert rec["fused_plate_text"] == "NOT READ"
    assert rec["plate_status"] == "NOT_READ"
    assert rec["is_synthetic"] is False
