"""Comprehensive Robustness Test Suite for TRACE Vehicle Appearance Re-ID Pipeline.

Validates:
1.  Normal crop produces exact 512-d finite embedding
2.  Tiny crop (<24px) rejection with explicit failure reason
3.  Boundary clipped crop handling
4.  Empty crop (0 pixels or None) rejection
5.  Grayscale crop conversion to 3-channel BGR and successful extraction
6.  BGRA crop conversion to 3-channel BGR and successful extraction
7.  Model inference exception handling (clean failure reason, no crash)
8.  NaN / Inf output handling (rejection and error reason)
9.  L2 normalization verification (|v| = 1.0)
10. Quality scoring logic (score_crop_quality differentiation)
11. Track-level best-crop quality upgrade logic
12. Idempotent DB upsert (replacing pending with complete)
13. Existing valid embedding preservation (never overwrite with None/failed)
14. Track ID safety across multiple cameras
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Camera, VehicleObservation
from app.modules.appearance import (
    extract_vehicle_embedding,
    get_appearance_extractor,
)
from app.modules.appearance.preprocessing import (
    score_crop_quality,
    validate_crop_detailed,
)
from app.modules.perception.persistence import (
    persist_fused_observation,
    upsert_observation_embedding,
)


@pytest.fixture(scope="module")
def extractor():
    """Shared appearance extractor instance."""
    return get_appearance_extractor()


@pytest.fixture(scope="module")
def db_engine():
    """Database engine fixture with backoff reset."""
    import app.modules.perception.persistence as pers
    pers._LAST_DB_ERROR_TIME = 0.0
    return create_engine(settings.DATABASE_URL_SYNC, echo=False)


# ---------------------------------------------------------------------------
# Test 1: Normal Crop Produces Exact 512-d Finite Embedding
# ---------------------------------------------------------------------------
def test_1_normal_crop_produces_512d_finite_embedding(extractor):
    crop = np.full((128, 128, 3), 120, dtype=np.uint8)
    crop[30:90, 30:90] = [0, 0, 200]  # Red vehicle center

    emb, reason = extractor.extract_with_reason(crop)
    assert emb is not None, f"Expected embedding, got None with reason: {reason}"
    assert reason is None
    assert isinstance(emb, list)
    assert len(emb) == 512
    assert all(np.isfinite(v) for v in emb)


# ---------------------------------------------------------------------------
# Test 2: Tiny Crop (<24px) Rejection With Failure Reason
# ---------------------------------------------------------------------------
def test_2_tiny_crop_rejection(extractor):
    tiny_crop = np.zeros((20, 20, 3), dtype=np.uint8)
    emb, reason = extractor.extract_with_reason(tiny_crop, min_size=24)
    assert emb is None
    assert reason == "crop_too_small"


# ---------------------------------------------------------------------------
# Test 3: Boundary Clipped Crop Handling
# ---------------------------------------------------------------------------
def test_3_boundary_clipped_crop_validation():
    # Frame shape is 1080x1920. Bbox is right against boundary (x1=0, y1=0)
    frame_shape = (1080, 1920, 3)
    clipped_bbox = [0, 0, 100, 100]
    center_bbox = [500, 500, 600, 600]

    crop = np.full((100, 100, 3), 150, dtype=np.uint8)
    score_clipped = score_crop_quality(crop, clipped_bbox, frame_shape, conf=0.9)
    score_center = score_crop_quality(crop, center_bbox, frame_shape, conf=0.9)

    assert score_center > score_clipped, "Center crop should have higher quality score than boundary-clipped crop"


# ---------------------------------------------------------------------------
# Test 4: Empty Crop Rejection
# ---------------------------------------------------------------------------
def test_4_empty_crop_rejection(extractor):
    emb_none, reason_none = extractor.extract_with_reason(None)
    assert emb_none is None
    assert reason_none == "missing_crop"

    empty_arr = np.zeros((0, 0, 3), dtype=np.uint8)
    emb_empty, reason_empty = extractor.extract_with_reason(empty_arr)
    assert emb_empty is None
    assert reason_empty == "empty_crop"


# ---------------------------------------------------------------------------
# Test 5: Grayscale Crop Auto-Conversion to 3-Channel BGR
# ---------------------------------------------------------------------------
def test_5_grayscale_crop_conversion(extractor):
    gray_crop = np.full((100, 100), 128, dtype=np.uint8)
    validated, reason = validate_crop_detailed(gray_crop, min_size=24)
    assert validated is not None
    assert validated.ndim == 3 and validated.shape[2] == 3

    emb, reason = extractor.extract_with_reason(gray_crop)
    assert emb is not None
    assert len(emb) == 512


# ---------------------------------------------------------------------------
# Test 6: BGRA Crop Auto-Conversion to 3-Channel BGR
# ---------------------------------------------------------------------------
def test_6_bgra_crop_conversion(extractor):
    bgra_crop = np.full((100, 100, 4), 160, dtype=np.uint8)
    validated, reason = validate_crop_detailed(bgra_crop, min_size=24)
    assert validated is not None
    assert validated.shape[2] == 3

    emb, reason = extractor.extract_with_reason(bgra_crop)
    assert emb is not None
    assert len(emb) == 512


# ---------------------------------------------------------------------------
# Test 7: Model Inference Exception Handling
# ---------------------------------------------------------------------------
def test_7_inference_exception_handling(extractor):
    crop = np.full((64, 64, 3), 100, dtype=np.uint8)

    with patch.object(extractor, "model", side_effect=RuntimeError("CUDA out of memory")):
        emb, reason = extractor.extract_with_reason(crop)
        assert emb is None
        assert reason == "inference_error"


# ---------------------------------------------------------------------------
# Test 8: NaN / Inf Output Handling
# ---------------------------------------------------------------------------
def test_8_nan_inf_output_handling(extractor):
    crop = np.full((64, 64, 3), 100, dtype=np.uint8)

    # Mock inference returning NaNs
    nan_tensor = torch.full((1, 512), float("nan"))
    with patch.object(extractor, "model", return_value=nan_tensor):
        emb, reason = extractor.extract_with_reason(crop)
        assert emb is None
        assert reason == "non_finite_output"


# ---------------------------------------------------------------------------
# Test 9: L2 Normalization Verification
# ---------------------------------------------------------------------------
def test_9_l2_normalization_verification(extractor):
    crop = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    emb, _ = extractor.extract_with_reason(crop)
    assert emb is not None

    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-4, f"L2 norm {norm} is not unit norm"


# ---------------------------------------------------------------------------
# Test 10: Quality Scoring Logic
# ---------------------------------------------------------------------------
def test_10_crop_quality_scoring():
    frame_shape = (1080, 1920, 3)

    # High quality: large, sharp, centered, high conf
    high_q = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    high_score = score_crop_quality(high_q, [800, 400, 1000, 600], frame_shape, conf=0.95)

    # Low quality: small, blurry, clipped, low conf
    low_q = np.full((30, 30, 3), 128, dtype=np.uint8)
    low_score = score_crop_quality(low_q, [0, 0, 30, 30], frame_shape, conf=0.4)

    assert high_score > low_score
    assert 0.0 <= low_score <= 1.0
    assert 0.0 <= high_score <= 1.0


# ---------------------------------------------------------------------------
# Test 11: Track-Level Best-Crop Quality Upgrade Logic
# ---------------------------------------------------------------------------
def test_11_track_level_best_crop_upgrade(extractor):
    crops = [
        np.full((32, 32, 3), 50, dtype=np.uint8),   # Low resolution
        np.random.randint(50, 200, (180, 180, 3), dtype=np.uint8), # High resolution & texture
        np.full((40, 40, 3), 80, dtype=np.uint8),   # Medium
    ]

    # extract_track_embedding sorts crops by score_crop_quality and extracts from best
    emb = extractor.extract_track_embedding(crops)
    assert emb is not None
    assert len(emb) == 512
    assert abs(np.linalg.norm(emb) - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# Test 12: Idempotent DB Upsert (Pending -> Complete)
# ---------------------------------------------------------------------------
def test_12_idempotent_db_upsert(db_engine):
    with Session(db_engine) as session:
        # Create test observation without embedding (pending)
        obs = persist_fused_observation(
            session=session,
            camera_id_str="c020",
            track_id=f"TRK-TEST-{uuid.uuid4().hex[:6]}",
            captured_at=datetime.now(timezone.utc),
            fused_plate_text="TEST12",
            fused_confidence=0.9,
            vehicle_type="car",
            vehicle_colour="white",
            appearance_embedding=None,
            embedding_status="pending",
            embedding_failure_reason="crop_pending_better_frame",
        )
        obs_id = obs.observation_id

    # Upsert with valid 512-d embedding
    dummy_emb = [0.0] * 512
    dummy_emb[0] = 1.0  # Unit vector
    with Session(db_engine) as session:
        success = upsert_observation_embedding(
            session=session,
            observation_id=obs_id,
            appearance_embedding=dummy_emb,
            embedding_status="complete",
        )
        assert success is True

    # Verify updated state
    with Session(db_engine) as session:
        updated = session.get(VehicleObservation, obs_id)
        assert updated is not None
        assert updated.embedding_status == "complete"
        assert updated.appearance_embedding is not None
        assert len(updated.appearance_embedding) == 512
        assert updated.embedding_attempts >= 1


# ---------------------------------------------------------------------------
# Test 13: Existing Valid Embedding Preservation
# ---------------------------------------------------------------------------
def test_13_existing_valid_embedding_preservation(db_engine):
    dummy_emb = [0.0] * 512
    dummy_emb[42] = 1.0

    with Session(db_engine) as session:
        obs = persist_fused_observation(
            session=session,
            camera_id_str="c020",
            track_id=f"TRK-TEST-{uuid.uuid4().hex[:6]}",
            captured_at=datetime.now(timezone.utc),
            fused_plate_text="TEST13",
            fused_confidence=0.9,
            vehicle_type="car",
            vehicle_colour="black",
            appearance_embedding=dummy_emb,
            embedding_status="complete",
        )
        obs_id = obs.observation_id

    # Attempt to overwrite with None / failed status
    with Session(db_engine) as session:
        upsert_observation_embedding(
            session=session,
            observation_id=obs_id,
            appearance_embedding=None,
            embedding_status="failed",
            embedding_failure_reason="test_overwrite_attempt",
        )

    # Verify original embedding was preserved
    with Session(db_engine) as session:
        checked = session.get(VehicleObservation, obs_id)
        assert checked.embedding_status == "complete"
        assert checked.appearance_embedding is not None
        assert checked.appearance_embedding[42] == 1.0


# ---------------------------------------------------------------------------
# Test 14: Track ID Safety Across Multiple Cameras
# ---------------------------------------------------------------------------
def test_14_track_id_safety_across_cameras(db_engine):
    shared_track_id = f"TRK-SHARED-{uuid.uuid4().hex[:6]}"
    emb_cam20 = [0.0] * 512
    emb_cam20[10] = 1.0
    emb_cam23 = [0.0] * 512
    emb_cam23[20] = 1.0

    with Session(db_engine) as session:
        obs1 = persist_fused_observation(
            session=session,
            camera_id_str="c020",
            track_id=shared_track_id,
            captured_at=datetime.now(timezone.utc),
            fused_plate_text="SHARE01",
            fused_confidence=0.85,
            vehicle_type="car",
            vehicle_colour="silver",
            appearance_embedding=emb_cam20,
            embedding_status="complete",
        )
        obs2 = persist_fused_observation(
            session=session,
            camera_id_str="c023",
            track_id=shared_track_id,
            captured_at=datetime.now(timezone.utc),
            fused_plate_text="SHARE01",
            fused_confidence=0.88,
            vehicle_type="car",
            vehicle_colour="silver",
            appearance_embedding=emb_cam23,
            embedding_status="complete",
        )

        assert obs1.observation_id != obs2.observation_id
        assert obs1.appearance_embedding[10] == 1.0
        assert obs2.appearance_embedding[20] == 1.0
