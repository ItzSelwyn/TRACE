"""Unit and integration tests for Layer 2 Multi-Modal Identity Fusion.

Updated for the multi-modal scoring engine:
  - Mode is auto-selected (ANPR vs CityFlowV2) based on plate availability
  - Unavailable modalities get weight redistributed (not zeroed out)
  - Type/colour are SOFT evidence (mismatch = partial score, not zero)
  - Temporal and camera-transition signals are new primary evidence

Tests:
  1. Identical plate + high OCR + same type + same colour -> CONFIRMED
  2. Slight plate difference + reasonable OCR + matching attributes -> candidate/confirmed
  3. Clearly different plate + low appearance -> NO_MATCH
  4. Same plate + different vehicle type -> score STILL high (soft penalty, not rejected)
  5. Same plate + different colour -> score STILL high (soft penalty, not rejected)
  6. Low OCR confidence -> lower plate evidence component (ANPR mode)
  7. Camera reliability weighting -> day vs night
  8. NOT READ plate values -> CityFlowV2 mode, no crash
  9. Same observation compared with itself -> returns None
 10. Same pair processed repeatedly -> no duplicate identity_matches records
 11. Three connected observations -> one canonical vehicle (may have null plate)
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import CanonicalVehicle, IdentityMatch, VehicleObservation
from app.modules.identity import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    compute_identity_score,
    levenshtein_similarity,
    match_observation_pair,
    pair_observations,
    select_reliability,
    _update_canonical_vehicles,
)
from app.modules.perception.persistence import persist_fused_observation, resolve_camera_uuid


def test_1_identical_plate_high_ocr_same_attributes():
    obs_a = {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.95, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"}
    obs_b = {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.95, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"}
    res = compute_identity_score(obs_a, obs_b)
    assert res["plate_similarity"] == 1.0
    assert res["mode"] == "ANPR"
    assert res["type_match"] is True
    assert res["colour_match"] is True
    assert res["identity_score"] >= CONFIRM_THRESHOLD
    assert res["status"] == "CONFIRMED"


def test_2_slight_plate_difference_candidate_or_confirmed():
    obs_a = {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.85, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"}
    obs_b = {"fused_plate_text": "TN37CY1235", "fused_confidence": 0.85, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"}
    res = compute_identity_score(obs_a, obs_b)
    assert res["plate_similarity"] == 0.90
    # ANPR mode: 1-char difference still likely candidate or confirmed
    assert res["identity_score"] >= CANDIDATE_THRESHOLD


def test_3_different_plate_low_appearance_low_score():
    obs_a = {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.60, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"}
    obs_b = {"fused_plate_text": "KA01AB9876", "fused_confidence": 0.60, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"}
    res = compute_identity_score(obs_a, obs_b, appearance_similarity=0.10)
    assert res["plate_similarity"] is not None
    assert res["plate_similarity"] <= 0.20
    assert res["identity_score"] < CANDIDATE_THRESHOLD
    assert res["status"] == "NO_MATCH"


def test_4_same_plate_different_type_score_stays_high():
    """Type mismatch is SOFT evidence — a matching plate should still produce high score."""
    same_type = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"},
    )
    diff_type = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "truck", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"},
    )
    assert diff_type["type_match"] is False
    # Mismatch causes some penalty, but should NOT drop below candidate (ANPR mode)
    assert diff_type["identity_score"] >= CANDIDATE_THRESHOLD
    # Score with same type is higher
    assert same_type["identity_score"] > diff_type["identity_score"]


def test_5_same_plate_different_colour_score_stays_high():
    """Colour mismatch is SOFT evidence — a matching plate should still produce high score."""
    same_colour = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"},
    )
    diff_colour = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "black", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"},
    )
    assert diff_colour["colour_match"] is False
    assert diff_colour["identity_score"] >= CANDIDATE_THRESHOLD
    assert same_colour["identity_score"] > diff_colour["identity_score"]


def test_6_low_ocr_confidence_decreases_plate_component():
    """In ANPR mode, lower OCR confidence means lower plate evidence."""
    high_ocr = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.95, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.95, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"},
    )
    low_ocr = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.30, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020", "captured_at": "2024-01-01T10:00:00Z"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.30, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023", "captured_at": "2024-01-01T10:05:00Z"},
    )
    assert high_ocr["ocr_confidence_component"] > low_ocr["ocr_confidence_component"]
    assert high_ocr["identity_score"] > low_ocr["identity_score"]


def test_7_camera_reliability_weighting_day_vs_night():
    profile = {"day_ocr_reliability": 0.95, "night_ocr_reliability": 0.70}
    rel_day = select_reliability(profile, "2026-09-04T12:00:00Z")
    rel_night = select_reliability(profile, "2026-09-04T22:00:00Z")
    assert rel_day == 0.95
    assert rel_night == 0.70

    score_day = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "captured_at": "2026-09-04T12:00:00Z", "camera_id": "c020"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "captured_at": "2026-09-04T12:00:00Z", "camera_id": "c023"},
        profile, profile,
    )
    score_night = compute_identity_score(
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "captured_at": "2026-09-04T22:00:00Z", "camera_id": "c020"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "captured_at": "2026-09-04T22:00:00Z", "camera_id": "c023"},
        profile, profile,
    )
    assert score_day["ocr_confidence_component"] > score_night["ocr_confidence_component"]


def test_8_not_read_plate_activates_cityflow_mode():
    """NOT READ plates must switch to CityFlowV2 mode — no crash, no artificial zero."""
    res = compute_identity_score(
        {"fused_plate_text": "NOT READ", "fused_confidence": 0.0, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c020"},
        {"fused_plate_text": "TN37CY1234", "fused_confidence": 0.90, "vehicle_type": "car", "vehicle_colour": "white", "camera_id": "c023"},
    )
    assert res["mode"] == "CITYFLOW"
    assert res["plate_similarity"] is None  # not penalised — unavailable
    # Score must not crash
    assert 0.0 <= res["identity_score"] <= 1.0


def test_9_same_observation_compared_with_itself():
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    with Session(engine) as session:
        obs = session.execute(select(VehicleObservation)).scalars().first()
        if obs:
            res = match_observation_pair(session, obs, obs, persist=False)
            assert res is None


def test_10_same_pair_processed_repeatedly_no_duplicates():
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    with Session(engine) as session:
        obs_a = persist_fused_observation(
            session=session, camera_id_str="c020", track_id="TRK-991",
            captured_at="2026-09-04T06:00:00Z", fused_plate_text="TN99ZZ1111", fused_confidence=0.95,
        )
        obs_b = persist_fused_observation(
            session=session, camera_id_str="c029", track_id="TRK-992",
            captured_at="2026-09-04T06:05:00Z", fused_plate_text="TN99ZZ1111", fused_confidence=0.95,
        )

        match_observation_pair(session, obs_a, obs_b, persist=True)
        count_1 = session.query(IdentityMatch).filter(
            (IdentityMatch.observation_id_a == obs_a.observation_id) |
            (IdentityMatch.observation_id_b == obs_a.observation_id)
        ).count()

        match_observation_pair(session, obs_a, obs_b, persist=True)
        count_2 = session.query(IdentityMatch).filter(
            (IdentityMatch.observation_id_a == obs_a.observation_id) |
            (IdentityMatch.observation_id_b == obs_a.observation_id)
        ).count()

        assert count_1 == count_2 == 1


def test_11_three_connected_observations_one_canonical_vehicle():
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    with Session(engine) as session:
        o1 = persist_fused_observation(session, "c020", "TRK-801", "2026-09-04T07:00:00Z", "TN88AA1234", 0.92)
        o2 = persist_fused_observation(session, "c023", "TRK-802", "2026-09-04T07:05:00Z", "TN88AA1234", 0.95)
        o3 = persist_fused_observation(session, "c035", "TRK-803", "2026-09-04T07:10:00Z", "TN88AA1234", 0.89)

        confirmed = [(o1, o2), (o2, o3)]
        _update_canonical_vehicles(session, confirmed)

        cv = session.execute(
            select(CanonicalVehicle).where(CanonicalVehicle.best_plate_text == "TN88AA1234")
        ).scalars().first()

        assert cv is not None
        assert cv.best_plate_text == "TN88AA1234"
        assert cv.first_seen_at <= o1.captured_at
        assert cv.last_seen_at >= o3.captured_at
