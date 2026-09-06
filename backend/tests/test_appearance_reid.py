"""Unit and Integration Tests for Vehicle Appearance / Re-ID Pipeline."""

import uuid
from datetime import datetime, timezone
import numpy as np
import pytest
import torch

from app.config import settings
from app.modules.appearance import (
    get_appearance_extractor,
    compute_appearance_similarity,
    compute_calibrated_similarity,
    compute_cosine_similarity,
    validate_crop,
)
from app.modules.identity.scoring import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    compute_identity_score,
)
from app.modules.identity.matcher import match_observation_pair
from app.db.models import VehicleObservation, IdentityMatch


# ---------------------------------------------------------------------------
# Test 1: Valid crop produces expected-dimensional finite embedding
# ---------------------------------------------------------------------------
def test_1_valid_crop_produces_finite_embedding():
    extractor = get_appearance_extractor()
    # Create realistic synthetic vehicle crop (e.g. 120x150 painted vehicle panel)
    crop = np.full((120, 150, 3), 180, dtype=np.uint8)
    crop[30:90, 20:130] = [220, 50, 50]  # Red vehicle body panel

    emb = extractor.extract(crop)
    assert emb is not None
    assert isinstance(emb, list)
    assert len(emb) == extractor.embedding_dim
    assert all(np.isfinite(v) for v in emb)


# ---------------------------------------------------------------------------
# Test 2: Embedding is L2-normalized
# ---------------------------------------------------------------------------
def test_2_embedding_is_l2_normalized():
    extractor = get_appearance_extractor()
    crop = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
    emb = extractor.extract(crop)
    assert emb is not None
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-4, f"Expected unit norm, got {norm}"


# ---------------------------------------------------------------------------
# Test 3: Same crop produces deterministic identical embedding
# ---------------------------------------------------------------------------
def test_3_same_crop_deterministic_embedding():
    extractor = get_appearance_extractor()
    crop = np.random.randint(50, 200, (120, 120, 3), dtype=np.uint8)
    emb1 = extractor.extract(crop)
    emb2 = extractor.extract(crop)
    assert emb1 is not None and emb2 is not None
    sim = compute_cosine_similarity(emb1, emb2)
    assert sim == 1.0


# ---------------------------------------------------------------------------
# Test 4: Visually distinct vehicles produce lower similarity than same vehicle
# ---------------------------------------------------------------------------
def test_4_distinct_vehicles_lower_similarity():
    extractor = get_appearance_extractor()
    # Vehicle A: Bright Blue Car
    veh_a1 = np.full((120, 150, 3), 200, dtype=np.uint8)
    veh_a1[30:90, 20:130] = [220, 50, 50]  # BGR blue
    # Vehicle A slightly shifted / noise
    veh_a2 = veh_a1.copy()
    veh_a2[32:92, 22:132] = [215, 55, 55]

    # Vehicle B: Dark Red Truck
    veh_b = np.full((120, 150, 3), 40, dtype=np.uint8)
    veh_b[20:100, 10:140] = [30, 30, 190]  # BGR red

    emb_a1 = extractor.extract(veh_a1)
    emb_a2 = extractor.extract(veh_a2)
    emb_b = extractor.extract(veh_b)

    sim_same = compute_cosine_similarity(emb_a1, emb_a2)
    sim_diff = compute_cosine_similarity(emb_a1, emb_b)

    assert sim_same is not None and sim_diff is not None
    assert sim_same > sim_diff, f"Expected same ({sim_same}) > diff ({sim_diff})"


# ---------------------------------------------------------------------------
# Test 5: Invalid crop returns None gracefully
# ---------------------------------------------------------------------------
def test_5_invalid_crop_returns_none():
    extractor = get_appearance_extractor()
    assert extractor.extract(None) is None
    assert extractor.extract(np.array([])) is None
    assert extractor.extract(np.zeros((0, 0, 3), dtype=np.uint8)) is None


# ---------------------------------------------------------------------------
# Test 6: Tiny crop (< min_size) returns None gracefully
# ---------------------------------------------------------------------------
def test_6_tiny_crop_returns_none():
    extractor = get_appearance_extractor()
    tiny = np.zeros((10, 10, 3), dtype=np.uint8)
    assert extractor.extract(tiny) is None


# ---------------------------------------------------------------------------
# Test 7: Model is reused (singleton pattern)
# ---------------------------------------------------------------------------
def test_7_model_is_reused():
    e1 = get_appearance_extractor()
    e2 = get_appearance_extractor()
    assert e1 is e2, "AppearanceExtractor must be a singleton instance"
    assert e1.model is e2.model


# ---------------------------------------------------------------------------
# Test 8: Real appearance embeddings reach compute_identity_score
# ---------------------------------------------------------------------------
def test_8_real_appearance_reaches_scorer():
    extractor = get_appearance_extractor()
    crop = np.full((100, 100, 3), 150, dtype=np.uint8)
    emb = extractor.extract(crop)

    app_sim = compute_appearance_similarity(emb, emb)
    assert app_sim == 1.0

    obs_a = {
        "fused_plate_text": "NOT READ", "fused_confidence": 0.0,
        "vehicle_type": "car", "vehicle_colour": "white",
        "captured_at": "2024-01-01T10:00:00Z", "camera_id": "c020"
    }
    obs_b = {
        "fused_plate_text": "NOT READ", "fused_confidence": 0.0,
        "vehicle_type": "car", "vehicle_colour": "white",
        "captured_at": "2024-01-01T10:05:00Z", "camera_id": "c023"
    }

    res = compute_identity_score(
        obs_a, obs_b,
        appearance_similarity=app_sim,
        camera_id_a="c020", camera_id_b="c023",
        time_gap_s=300,
    )
    assert res["appearance_similarity"] == 1.0
    assert res["mode"] == "CITYFLOW"
    assert res["identity_score"] >= CONFIRM_THRESHOLD


# ---------------------------------------------------------------------------
# Test 9: CityFlow visual-only observation works with plate=None
# ---------------------------------------------------------------------------
def test_9_cityflow_visual_only_with_plate_none():
    obs_a = {"fused_plate_text": None, "vehicle_type": "car", "vehicle_colour": "white"}
    obs_b = {"fused_plate_text": None, "vehicle_type": "car", "vehicle_colour": "white"}

    res = compute_identity_score(
        obs_a, obs_b,
        appearance_similarity=0.90,
        camera_id_a="c020", camera_id_b="c023",
        time_gap_s=300,
    )
    assert res["plate_similarity"] is None
    assert res["mode"] == "CITYFLOW"
    assert res["identity_score"] >= CONFIRM_THRESHOLD


# ---------------------------------------------------------------------------
# Test 10: Type mismatch remains a soft penalty
# ---------------------------------------------------------------------------
def test_10_type_mismatch_is_soft():
    res = compute_identity_score(
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "white"},
        {"fused_plate_text": "NOT READ", "vehicle_type": "truck", "vehicle_colour": "white"},
        appearance_similarity=0.88,
        camera_id_a="c020", camera_id_b="c023",
        time_gap_s=300,
    )
    assert res["type_match"] is False
    assert res["type_score"] == 0.4
    assert res["identity_score"] >= CONFIRM_THRESHOLD


# ---------------------------------------------------------------------------
# Test 11: Colour mismatch remains a soft penalty
# ---------------------------------------------------------------------------
def test_11_colour_mismatch_is_soft():
    res = compute_identity_score(
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "white"},
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "black"},
        appearance_similarity=0.88,
        camera_id_a="c020", camera_id_b="c023",
        time_gap_s=300,
    )
    assert res["colour_match"] is False
    assert res["colour_score"] == 0.3
    assert res["identity_score"] >= CONFIRM_THRESHOLD


# ---------------------------------------------------------------------------
# Test 12: Temporal impossibility reduces the identity score
# ---------------------------------------------------------------------------
def test_12_temporal_impossibility_penalizes_score():
    res_valid = compute_identity_score(
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "white"},
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "white"},
        appearance_similarity=0.85,
        camera_id_a="c020", camera_id_b="c023",
        time_gap_s=300.0,
    )
    res_impossible = compute_identity_score(
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "white"},
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "white"},
        appearance_similarity=0.85,
        camera_id_a="c020", camera_id_b="c023",
        time_gap_s=10.0,  # Impossible (min 120s)
    )
    assert res_impossible["temporal_score"] == 0.0
    assert res_impossible["identity_score"] < res_valid["identity_score"]


# ---------------------------------------------------------------------------
# Test 13: Different vehicles are not automatically confirmed
# ---------------------------------------------------------------------------
def test_13_different_vehicles_not_confirmed():
    res = compute_identity_score(
        {"fused_plate_text": "NOT READ", "vehicle_type": "car", "vehicle_colour": "white"},
        {"fused_plate_text": "NOT READ", "vehicle_type": "truck", "vehicle_colour": "black"},
        appearance_similarity=0.15,
        camera_id_a="c020", camera_id_b="c023",
        time_gap_s=10.0,
    )
    assert res["identity_score"] < CANDIDATE_THRESHOLD
    assert res["status"] == "NO_MATCH"


# ---------------------------------------------------------------------------
# Test 14: Duplicate match prevention still works
# ---------------------------------------------------------------------------
def test_14_duplicate_match_prevention():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.modules.perception.persistence import persist_fused_observation

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    with Session(engine) as s:
        obs_a = persist_fused_observation(s, "c020", "TRK-D1", "2026-09-06T12:00:00Z", "NOT READ", 0.0)
        obs_b = persist_fused_observation(s, "c023", "TRK-D2", "2026-09-06T12:05:00Z", "NOT READ", 0.0)
        if obs_a and obs_b:
            r1 = match_observation_pair(s, obs_a, obs_b, persist=True, appearance_similarity=0.9)
            r2 = match_observation_pair(s, obs_a, obs_b, persist=True, appearance_similarity=0.9)
            cnt = s.query(IdentityMatch).filter(
                (IdentityMatch.observation_id_a == obs_a.observation_id) |
                (IdentityMatch.observation_id_b == obs_a.observation_id)
            ).count()
            assert cnt == 1


# ---------------------------------------------------------------------------
# Test 15: Missing all modalities CANNOT produce an artificial perfect score (Requirement 15)
# ---------------------------------------------------------------------------
def test_15_missing_modalities_cannot_produce_false_confirmed():
    """A pair with no plate and no appearance must NEVER receive a confirmed or high-confidence match."""
    res = compute_identity_score(
        {"fused_plate_text": "NOT READ", "fused_confidence": 0.0, "vehicle_type": "car", "vehicle_colour": "white"},
        {"fused_plate_text": "NOT READ", "fused_confidence": 0.0, "vehicle_type": "car", "vehicle_colour": "white"},
        appearance_similarity=None,  # No visual appearance
    )
    assert res["status"] == "NO_MATCH", f"Expected NO_MATCH without primary evidence, got {res['status']}"
    assert res["identity_score"] < CANDIDATE_THRESHOLD, (
        f"Score must be < {CANDIDATE_THRESHOLD} when primary evidence is missing, got {res['identity_score']}"
    )
    assert res["weight_debug"].get("primary_evidence_missing") is True
