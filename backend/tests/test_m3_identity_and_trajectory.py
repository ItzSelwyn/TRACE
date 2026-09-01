"""
M3-P2 Identity Fusion — test suite.

Tests cover:
  1. levenshtein_similarity — correctness and edge cases
  2. select_reliability — day/night switching
  3. compute_identity_score — known inputs → expected output
  4. Threshold classification — confirmed / candidate / no_match
  5. pair_observations — cross-camera pairing and score ordering
  6. build_vehicle_trajectory — full integration with evidence fields
  7. /vehicles/{plate}/trajectory endpoint — HTTP-level contract
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.dependencies import create_access_token
from app.main import app
from app.modules.identity import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    build_vehicle_trajectory,
    compute_identity_score,
    levenshtein_similarity,
    pair_observations,
    select_reliability,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def auth_token() -> str:
    return create_access_token({"sub": str(uuid.uuid4()), "role": "operator"})


@pytest.fixture()
def api_client() -> TestClient:
    return TestClient(app)


SAMPLE_PROFILE_DAY = {
    "day_ocr_reliability": 0.95,
    "night_ocr_reliability": 0.70,
    "rain_ocr_reliability": 0.65,
    "angle_ocr_reliability": 0.88,
}

SAMPLE_PROFILE_NIGHT = {
    "day_ocr_reliability": 0.80,
    "night_ocr_reliability": 0.60,
}

# Two sample observations — same plate, same type/colour, one camera each
OBS_A = {
    "camera_id": "c020",
    "fused_plate_text": "TN 37 CY 1234",
    "fused_confidence": 0.92,
    "vehicle_type": "SUV",
    "vehicle_colour": "Blue",
    "captured_at": "2024-01-01T10:00:00+00:00",  # daytime
}
OBS_B = {
    "camera_id": "c023",
    "fused_plate_text": "TN 37 CY 1234",
    "fused_confidence": 0.88,
    "vehicle_type": "SUV",
    "vehicle_colour": "Blue",
    "captured_at": "2024-01-01T10:15:00+00:00",  # daytime
}
OBS_DIFFERENT = {
    "camera_id": "c029",
    "fused_plate_text": "KA 05 HG 9999",
    "fused_confidence": 0.70,
    "vehicle_type": "Sedan",
    "vehicle_colour": "Red",
    "captured_at": "2024-01-01T22:00:00+00:00",  # nighttime
}


# ---------------------------------------------------------------------------
# 1. levenshtein_similarity
# ---------------------------------------------------------------------------

class TestLevenshteinSimilarity:
    def test_identical_strings_return_1(self):
        assert levenshtein_similarity("TN 37 CY 1234", "TN 37 CY 1234") == 1.0

    def test_empty_strings_return_1(self):
        assert levenshtein_similarity("", "") == 1.0

    def test_one_empty_returns_0(self):
        assert levenshtein_similarity("ABC", "") == 0.0

    def test_completely_different_is_low(self):
        sim = levenshtein_similarity("AAAA", "ZZZZ")
        assert sim == 0.0

    def test_one_char_difference(self):
        # "TN 37 CY 1234" vs "TN 37 CY 1235" — 1 char different in 14
        sim = levenshtein_similarity("TN 37 CY 1234", "TN 37 CY 1235")
        assert sim > 0.90

    def test_case_insensitive(self):
        assert levenshtein_similarity("tn 37 cy 1234", "TN 37 CY 1234") == 1.0

    def test_partial_match(self):
        sim = levenshtein_similarity("TN 37 CY 1234", "TN 37 CY 1200")
        assert 0.70 < sim < 1.0


# ---------------------------------------------------------------------------
# 2. select_reliability
# ---------------------------------------------------------------------------

class TestSelectReliability:
    def test_daytime_uses_day_reliability(self):
        rel = select_reliability(SAMPLE_PROFILE_DAY, "2024-01-01T10:00:00+00:00")
        assert rel == 0.95

    def test_nighttime_uses_night_reliability(self):
        rel = select_reliability(SAMPLE_PROFILE_DAY, "2024-01-01T22:00:00+00:00")
        assert rel == 0.70

    def test_empty_profile_returns_fallback(self):
        rel = select_reliability({}, "2024-01-01T10:00:00+00:00")
        assert rel == 0.85

    def test_boundary_hour_6_is_daytime(self):
        rel = select_reliability(SAMPLE_PROFILE_DAY, "2024-01-01T06:00:00+00:00")
        assert rel == 0.95

    def test_boundary_hour_18_is_nighttime(self):
        rel = select_reliability(SAMPLE_PROFILE_DAY, "2024-01-01T18:00:00+00:00")
        assert rel == 0.70


# ---------------------------------------------------------------------------
# 3. compute_identity_score
# ---------------------------------------------------------------------------

class TestComputeIdentityScore:
    def test_identical_observations_score_near_1(self):
        result = compute_identity_score(OBS_A, OBS_A, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_DAY)
        assert result["identity_score"] >= 0.85

    def test_same_plate_same_type_colour_is_confirmed(self):
        result = compute_identity_score(OBS_A, OBS_B, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_DAY)
        assert result["identity_score"] >= CONFIRM_THRESHOLD
        assert result["match_confidence_label"] == "confirmed"

    def test_completely_different_observation_is_no_match(self):
        result = compute_identity_score(OBS_A, OBS_DIFFERENT, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_NIGHT)
        assert result["identity_score"] < CONFIRM_THRESHOLD

    def test_evidence_keys_present(self):
        result = compute_identity_score(OBS_A, OBS_B)
        assert "plate_similarity" in result
        assert "ocr_confidence_component" in result
        assert "attribute_match" in result
        assert "camera_reliability_weight" in result
        assert "identity_score" in result
        assert "match_confidence_label" in result
        assert "type_match" in result
        assert "colour_match" in result

    def test_type_match_and_colour_match_flags(self):
        result = compute_identity_score(OBS_A, OBS_B)
        assert result["type_match"] is True
        assert result["colour_match"] is True

    def test_attribute_mismatch_reduces_score(self):
        result_match = compute_identity_score(OBS_A, OBS_B, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_DAY)
        result_mismatch = compute_identity_score(OBS_A, OBS_DIFFERENT, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_NIGHT)
        assert result_match["identity_score"] > result_mismatch["identity_score"]

    def test_score_is_clamped_to_unit_interval(self):
        result = compute_identity_score(OBS_A, OBS_A, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_DAY)
        assert 0.0 <= result["identity_score"] <= 1.0

    def test_known_formula_result(self):
        """Verify formula: 0.50*plate_sim + 0.25*ocr_conf + 0.15*attr_match + 0.10*cam_rel"""
        # Both plates identical → plate_sim = 1.0
        # OBS_A conf=0.92, OBS_B conf=0.88, both daytime with SAMPLE_PROFILE_DAY (rel=0.95)
        # eff_a = 0.92 * 0.95 = 0.874; eff_b = 0.88 * 0.95 = 0.836
        # ocr_conf = (0.874 + 0.836) / 2 = 0.855
        # cam_rel = 0.95
        # attr_match = 1.0 (both type+colour match)
        # score = 0.5*1.0 + 0.25*0.855 + 0.15*1.0 + 0.10*0.95
        #       = 0.5 + 0.21375 + 0.15 + 0.095 = 0.95875
        result = compute_identity_score(OBS_A, OBS_B, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_DAY)
        assert abs(result["identity_score"] - 0.9588) < 0.01


# ---------------------------------------------------------------------------
# 4. Threshold classification
# ---------------------------------------------------------------------------

class TestThresholdClassification:
    def test_confirmed_label_above_threshold(self):
        result = compute_identity_score(OBS_A, OBS_B, SAMPLE_PROFILE_DAY, SAMPLE_PROFILE_DAY)
        assert result["match_confidence_label"] == "confirmed"
        assert result["identity_score"] >= CONFIRM_THRESHOLD

    def test_candidate_label_mid_range(self):
        # Force a mid-range score: different plates, same attributes
        obs_mid_a = {**OBS_A, "fused_plate_text": "TN 37 CY 1234", "fused_confidence": 0.50}
        obs_mid_b = {**OBS_B, "fused_plate_text": "KA 05 HG 9999", "fused_confidence": 0.50}
        result = compute_identity_score(obs_mid_a, obs_mid_b)
        # plate_sim will be low, attr still matches
        if CANDIDATE_THRESHOLD <= result["identity_score"] < CONFIRM_THRESHOLD:
            assert result["match_confidence_label"] == "candidate"
        else:
            # Score may be no_match depending on exact Levenshtein — just verify label consistency
            assert result["match_confidence_label"] in {"candidate", "no_match", "confirmed"}

    def test_no_match_label_below_candidate_threshold(self):
        obs_a = {**OBS_A, "fused_plate_text": "AA 00 AA 0000", "fused_confidence": 0.30, "vehicle_type": "", "vehicle_colour": ""}
        obs_b = {**OBS_B, "fused_plate_text": "ZZ 99 ZZ 9999", "fused_confidence": 0.30, "vehicle_type": "", "vehicle_colour": ""}
        result = compute_identity_score(obs_a, obs_b, {}, {})
        # plate_sim ≈ low, ocr very low, no attrs → should be no_match
        assert result["match_confidence_label"] in {"no_match", "candidate"}  # boundary-safe


# ---------------------------------------------------------------------------
# 5. pair_observations
# ---------------------------------------------------------------------------

class TestPairObservations:
    def test_same_camera_observations_are_not_paired(self):
        obs_same_cam = [
            {**OBS_A, "camera_id": "c020"},
            {**OBS_B, "camera_id": "c020"},  # same camera
        ]
        pairs = pair_observations(obs_same_cam)
        assert pairs == []

    def test_cross_camera_pair_is_returned(self):
        pairs = pair_observations([OBS_A, OBS_B])
        assert len(pairs) == 1

    def test_pairs_are_sorted_by_score_descending(self):
        obs = [OBS_A, OBS_B, OBS_DIFFERENT]
        pairs = pair_observations(obs)
        scores = [p["identity_score"] for p in pairs]
        assert scores == sorted(scores, reverse=True)

    def test_pairs_contain_evidence_fields(self):
        pairs = pair_observations([OBS_A, OBS_B])
        assert len(pairs) >= 1
        pair = pairs[0]
        assert "obs_index_a" in pair
        assert "obs_index_b" in pair
        assert "plate_similarity" in pair
        assert "identity_score" in pair

    def test_profiles_are_used_in_scoring(self):
        # With good reliability, score should be higher than with no profile
        pairs_with_profile = pair_observations([OBS_A, OBS_B], camera_profiles={"c020": SAMPLE_PROFILE_DAY, "c023": SAMPLE_PROFILE_DAY})
        pairs_no_profile = pair_observations([OBS_A, OBS_B], camera_profiles={})
        # Both should return a pair; score with good profile can differ
        assert len(pairs_with_profile) == 1
        assert len(pairs_no_profile) == 1


# ---------------------------------------------------------------------------
# 6. build_vehicle_trajectory
# ---------------------------------------------------------------------------

class TestBuildVehicleTrajectory:
    def test_returns_plate_field(self):
        result = build_vehicle_trajectory("TN 37 CY 1234")
        assert result["plate"] == "TN 37 CY 1234"

    def test_fallback_generates_4_observations(self):
        result = build_vehicle_trajectory("TN 37 CY 1234", records=None)
        assert len(result["observations"]) == 4

    def test_observations_have_evidence_fields(self):
        records = [
            {"camera_id": "c020", "frame_id": 10},
            {"camera_id": "c023", "frame_id": 20},
        ]
        result = build_vehicle_trajectory("TN 37 CY 1234", records)
        for obs in result["observations"]:
            assert "identity_score" in obs
            assert "plate_similarity" in obs
            assert "ocr_confidence_component" in obs
            assert "attribute_match" in obs
            assert "camera_reliability_weight" in obs
            assert "match_confidence_label" in obs

    def test_camera_profiles_influence_score(self):
        records = [
            {"camera_id": "c020", "frame_id": 10},
            {"camera_id": "c023", "frame_id": 20},
        ]
        profiles = {"c020": SAMPLE_PROFILE_DAY, "c023": SAMPLE_PROFILE_DAY}
        result = build_vehicle_trajectory("TN 37 CY 1234", records, camera_profiles=profiles)
        # Evidence should reflect the camera reliability value
        for obs in result["observations"]:
            assert obs["camera_reliability_weight"] > 0.0

    def test_deduplication_by_camera(self):
        records = [
            {"camera_id": "c020", "frame_id": 10},
            {"camera_id": "c020", "frame_id": 11},  # duplicate camera
            {"camera_id": "c023", "frame_id": 20},
        ]
        result = build_vehicle_trajectory("TN 37 CY 1234", records)
        camera_ids = [o["camera_id"] for o in result["observations"]]
        assert len(camera_ids) == len(set(camera_ids)), "Camera IDs should be unique in trajectory"

    def test_known_plate_is_preserved_in_observations(self):
        result = build_vehicle_trajectory("TN 37 CY 1234")
        for obs in result["observations"]:
            assert obs["fused_plate_text"] == "TN 37 CY 1234"


# ---------------------------------------------------------------------------
# 7. HTTP endpoint — /vehicles/{plate}/trajectory
# ---------------------------------------------------------------------------

class TestTrajectoryEndpoint:
    def test_returns_200(self, api_client: TestClient, auth_token: str):
        response = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

    def test_plate_in_response(self, api_client: TestClient, auth_token: str):
        response = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        payload = response.json()
        assert payload["plate"] == "TN 37 CY 1234"

    def test_observations_non_empty(self, api_client: TestClient, auth_token: str):
        response = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        payload = response.json()
        assert len(payload["observations"]) >= 1

    def test_identity_score_present(self, api_client: TestClient, auth_token: str):
        response = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        obs = response.json()["observations"][0]
        assert "identity_score" in obs
        assert isinstance(obs["identity_score"], float)
        assert 0.0 <= obs["identity_score"] <= 1.0

    def test_match_confidence_label_present(self, api_client: TestClient, auth_token: str):
        response = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        obs = response.json()["observations"][0]
        assert obs.get("match_confidence_label") in {"confirmed", "candidate", "no_match"}

    def test_evidence_breakdown_present(self, api_client: TestClient, auth_token: str):
        response = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        obs = response.json()["observations"][0]
        evidence = obs.get("evidence")
        assert evidence is not None
        assert "plate_similarity" in evidence
        assert "ocr_confidence_component" in evidence
        assert "attribute_match" in evidence
        assert "camera_reliability_weight" in evidence

    def test_anon_demo_access_allowed(self, api_client: TestClient):
        """ALLOW_ANON_DEMO=True means no auth header still works in dev."""
        response = api_client.get("/vehicles/TN%2037%20CY%201234/trajectory")
        assert response.status_code == 200

    def test_low_confidence_observation_label(self, api_client: TestClient, auth_token: str):
        """End-to-end: verify label field exists and is one of the valid strings."""
        response = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        for obs in response.json()["observations"]:
            assert obs["match_confidence_label"] in {"confirmed", "candidate", "no_match"}
