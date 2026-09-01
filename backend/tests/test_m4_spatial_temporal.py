"""
M4-P2 Spatial-Temporal Reasoning — test suite.

Tests cover:
  1. Road graph loading and adjacency
  2. Shortest path (Dijkstra)
  3. Reachability check
  4. Compute implied speed
  5. Impossible journey detection
  6. Camera inconsistency detection
  7. Duplicate plate detection
  8. Full trajectory reconstruction
  9. All 4 staged QA scenarios from data/ground_truth/staged_scenarios.json
 10. HTTP endpoint — anomaly fields in response
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.dependencies import create_access_token
from app.main import app
from app.modules.spatial_temporal import (
    check_impossible_journey,
    compute_implied_speed,
    detect_camera_inconsistency,
    detect_duplicate_plates,
    reconstruct_trajectory,
    reachability_check,
    shortest_path,
)
from app.modules.spatial_temporal.road_graph import build_road_graph, load_cameras, load_edges

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STAGED = _PROJECT_ROOT / "data" / "ground_truth" / "staged_scenarios.json"

# ---------------------------------------------------------------------------
# Minimal in-memory test graph — 3 cameras, 2 edges
# ---------------------------------------------------------------------------
_TEST_EDGES = [
    {
        "edge_id": "e-test-01",
        "from_camera_id": "cam-A",
        "to_camera_id": "cam-B",
        "distance_km": 2.0,
        "min_travel_time_s": 120,
        "max_travel_time_s": 600,
        "speed_limit_kmph": 60,
    },
    {
        "edge_id": "e-test-02",
        "from_camera_id": "cam-B",
        "to_camera_id": "cam-C",
        "distance_km": 3.0,
        "min_travel_time_s": 180,
        "max_travel_time_s": 900,
        "speed_limit_kmph": 60,
    },
]
_TEST_GRAPH = build_road_graph(edges=_TEST_EDGES, cameras={})

# Timestamp helpers
_T0 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def _ts(delta_s: float) -> str:
    return (_T0 + timedelta(seconds=delta_s)).isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def auth_token() -> str:
    return create_access_token({"sub": str(uuid.uuid4()), "role": "operator"})


@pytest.fixture()
def api_client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Road graph loading
# ---------------------------------------------------------------------------

class TestRoadGraphLoading:
    def test_load_edges_returns_list(self):
        edges = load_edges()
        # Seed file has 16 edges
        assert isinstance(edges, list)
        assert len(edges) >= 10

    def test_load_cameras_returns_dict(self):
        cams = load_cameras()
        assert isinstance(cams, dict)
        assert len(cams) >= 10  # 10 Bangalore cameras

    def test_build_road_graph_has_adj(self):
        g = build_road_graph()
        assert "adj" in g
        assert "edges" in g

    def test_build_road_graph_test_edges(self):
        adj = _TEST_GRAPH["adj"]
        assert "cam-A" in adj
        assert any(n["to_camera_id"] == "cam-B" for n in adj["cam-A"])

    def test_adj_contains_travel_time_fields(self):
        for neighbour in _TEST_GRAPH["adj"]["cam-A"]:
            assert "min_travel_time_s" in neighbour
            assert "speed_limit_kmph" in neighbour
            assert "distance_km" in neighbour


# ---------------------------------------------------------------------------
# 2. Shortest path
# ---------------------------------------------------------------------------

class TestShortestPath:
    def test_direct_edge(self):
        min_t, path = shortest_path(_TEST_GRAPH, "cam-A", "cam-B")
        assert min_t == 120
        assert path == ["cam-A", "cam-B"]

    def test_two_hop_path(self):
        min_t, path = shortest_path(_TEST_GRAPH, "cam-A", "cam-C")
        assert min_t == 300  # 120 + 180
        assert path == ["cam-A", "cam-B", "cam-C"]

    def test_same_node_returns_zero(self):
        min_t, path = shortest_path(_TEST_GRAPH, "cam-A", "cam-A")
        assert min_t == 0
        assert path == ["cam-A"]

    def test_no_path_returns_inf(self):
        min_t, path = shortest_path(_TEST_GRAPH, "cam-A", "cam-UNKNOWN")
        assert min_t == float("inf")
        assert path == []

    def test_real_graph_c1_to_c5(self):
        # Real seed graph: c1→c2→c3→c4→c5 or c1→c3→c5
        g = build_road_graph()
        min_t, path = shortest_path(g, "c1000000-0000-0000-0000-000000000001", "c5000000-0000-0000-0000-000000000005")
        assert min_t < float("inf")
        assert path[0] == "c1000000-0000-0000-0000-000000000001"
        assert path[-1] == "c5000000-0000-0000-0000-000000000005"


# ---------------------------------------------------------------------------
# 3. Reachability check
# ---------------------------------------------------------------------------

class TestReachabilityCheck:
    def test_reachable_when_gap_exceeds_min(self):
        result = reachability_check("cam-A", "cam-B", time_gap_s=200, graph=_TEST_GRAPH)
        assert result["reachable"] is True
        assert result["min_travel_time_s"] == 120

    def test_not_reachable_when_gap_below_min(self):
        result = reachability_check("cam-A", "cam-B", time_gap_s=60, graph=_TEST_GRAPH)
        assert result["reachable"] is False

    def test_exact_boundary_is_reachable(self):
        result = reachability_check("cam-A", "cam-B", time_gap_s=120, graph=_TEST_GRAPH)
        assert result["reachable"] is True

    def test_no_path_returns_not_reachable(self):
        result = reachability_check("cam-A", "cam-UNKNOWN", time_gap_s=9999, graph=_TEST_GRAPH)
        assert result["reachable"] is False

    def test_path_is_returned(self):
        result = reachability_check("cam-A", "cam-C", time_gap_s=400, graph=_TEST_GRAPH)
        assert result["path"] == ["cam-A", "cam-B", "cam-C"]


# ---------------------------------------------------------------------------
# 4. Implied speed
# ---------------------------------------------------------------------------

class TestComputeImpliedSpeed:
    def test_basic_speed(self):
        # 2 km in 120s = 2 / (120/3600) = 60 km/h
        speed = compute_implied_speed(2.0, 120)
        assert speed == pytest.approx(60.0, abs=0.1)

    def test_zero_time_returns_zero(self):
        assert compute_implied_speed(5.0, 0) == 0.0

    def test_negative_time_returns_zero(self):
        assert compute_implied_speed(5.0, -10) == 0.0

    def test_very_fast(self):
        # 2 km in 10 seconds = 720 km/h
        speed = compute_implied_speed(2.0, 10)
        assert speed == pytest.approx(720.0, abs=1.0)


# ---------------------------------------------------------------------------
# 5. Impossible journey detection
# ---------------------------------------------------------------------------

class TestImpossibleJourney:
    def test_normal_journey_is_not_impossible(self):
        # cam-A→cam-B: 2km, speed_limit=60. Gap=200s → 36 km/h < 90 (60*1.5)
        result = check_impossible_journey("cam-A", "cam-B", 200, _TEST_GRAPH, multiplier=1.5)
        assert result["is_impossible_journey"] is False
        assert result["implied_speed_kmph"] == pytest.approx(36.0, abs=0.5)

    def test_too_fast_time_is_flagged(self):
        # Gap = 60s < min_travel_time_s = 120s → impossible
        result = check_impossible_journey("cam-A", "cam-B", 60, _TEST_GRAPH, multiplier=1.5)
        assert result["is_impossible_journey"] is True
        assert result["reason"] == "too_fast_time"

    def test_speed_exceeds_limit_times_multiplier(self):
        # cam-A→cam-B: 2km, speed_limit=60, multiplier=1.5 → ceiling=90 km/h
        # time_gap=10s → implied = 720 km/h > 90 → impossible
        result = check_impossible_journey("cam-A", "cam-B", 10, _TEST_GRAPH, multiplier=1.5)
        assert result["is_impossible_journey"] is True

    def test_unknown_destination_is_flagged(self):
        result = check_impossible_journey("cam-A", "cam-UNKNOWN", 9999, _TEST_GRAPH)
        assert result["is_impossible_journey"] is True

    def test_implied_speed_returned_when_available(self):
        result = check_impossible_journey("cam-A", "cam-B", 200, _TEST_GRAPH)
        assert result["implied_speed_kmph"] is not None
        assert result["implied_speed_kmph"] > 0


# ---------------------------------------------------------------------------
# 6. Camera inconsistency detection
# ---------------------------------------------------------------------------

class TestCameraInconsistency:
    def test_backward_timestamp_flagged(self):
        obs = [
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(100)},
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(50)},  # backward
        ]
        result = detect_camera_inconsistency(obs)
        assert len(result) == 1
        assert result[0]["anomaly_type"] == "camera_inconsistency"

    def test_forward_timestamps_no_flag(self):
        obs = [
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(0)},
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(30)},
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(60)},
        ]
        result = detect_camera_inconsistency(obs)
        assert result == []

    def test_different_tracks_not_compared(self):
        obs = [
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(100)},
            {"camera_id": "cam-X", "track_id": "t2", "captured_at": _ts(50)},  # different track
        ]
        result = detect_camera_inconsistency(obs)
        assert result == []

    def test_different_cameras_not_compared(self):
        obs = [
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(100)},
            {"camera_id": "cam-Y", "track_id": "t1", "captured_at": _ts(50)},  # different camera
        ]
        result = detect_camera_inconsistency(obs)
        assert result == []

    def test_returns_correct_obs_index(self):
        obs = [
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(100)},
            {"camera_id": "cam-X", "track_id": "t1", "captured_at": _ts(50)},
        ]
        result = detect_camera_inconsistency(obs)
        assert result[0]["obs_index"] == 1  # second observation is the backward one


# ---------------------------------------------------------------------------
# 7. Duplicate plate detection
# ---------------------------------------------------------------------------

class TestDuplicatePlates:
    def test_simultaneous_unreachable_cameras_flagged(self):
        # cam-A and cam-C: min_travel_time = 300s, gap = 5s → duplicate
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "XX 00 YY 1234",
             "captured_at": _ts(0)},
            {"camera_id": "cam-C", "track_id": "t2", "fused_plate_text": "XX 00 YY 1234",
             "captured_at": _ts(5)},
        ]
        result = detect_duplicate_plates(obs, _TEST_GRAPH, overlap_tolerance_s=60)
        assert len(result) == 1
        assert result[0]["anomaly_type"] == "duplicate_plate"
        assert result[0]["plate_text"] == "XX 00 YY 1234"

    def test_same_camera_not_flagged(self):
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "AB 01",
             "captured_at": _ts(0)},
            {"camera_id": "cam-A", "track_id": "t2", "fused_plate_text": "AB 01",
             "captured_at": _ts(5)},
        ]
        result = detect_duplicate_plates(obs, _TEST_GRAPH)
        assert result == []

    def test_different_plates_not_flagged(self):
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "PLATE-1",
             "captured_at": _ts(0)},
            {"camera_id": "cam-C", "track_id": "t2", "fused_plate_text": "PLATE-2",
             "captured_at": _ts(5)},
        ]
        result = detect_duplicate_plates(obs, _TEST_GRAPH)
        assert result == []

    def test_wide_gap_not_flagged(self):
        # Gap = 3600s (1 hour) — well outside overlap_tolerance
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "PLATE-X",
             "captured_at": _ts(0)},
            {"camera_id": "cam-C", "track_id": "t2", "fused_plate_text": "PLATE-X",
             "captured_at": _ts(3600)},
        ]
        result = detect_duplicate_plates(obs, _TEST_GRAPH, overlap_tolerance_s=60)
        assert result == []


# ---------------------------------------------------------------------------
# 8. Full trajectory reconstruction
# ---------------------------------------------------------------------------

class TestReconstructTrajectory:
    def test_empty_observations_returns_empty(self):
        result = reconstruct_trajectory("TN 01 AA 0000", [])
        assert result["observations"] == []
        assert result["anomaly_flags"] == []

    def test_chronological_sort(self):
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "P1",
             "fused_confidence": 0.9, "vehicle_type": "car", "vehicle_colour": "red",
             "captured_at": _ts(200), "identity_score": 0.9, "plate_similarity": 1.0,
             "ocr_confidence_component": 0.85, "attribute_match": 1.0,
             "camera_reliability_weight": 0.9, "match_confidence_label": "confirmed"},
            {"camera_id": "cam-B", "track_id": "t1", "fused_plate_text": "P1",
             "fused_confidence": 0.88, "vehicle_type": "car", "vehicle_colour": "red",
             "captured_at": _ts(0), "identity_score": 0.9, "plate_similarity": 1.0,
             "ocr_confidence_component": 0.83, "attribute_match": 1.0,
             "camera_reliability_weight": 0.9, "match_confidence_label": "confirmed"},
        ]
        result = reconstruct_trajectory("P1", obs, _TEST_GRAPH)
        timestamps = [o["captured_at"] for o in result["observations"]]
        assert timestamps[0] < timestamps[1]  # sorted

    def test_normal_trajectory_no_anomalies(self):
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "NORMAL",
             "fused_confidence": 0.95, "vehicle_type": "SUV", "vehicle_colour": "Blue",
             "captured_at": _ts(0), "identity_score": 0.95, "plate_similarity": 1.0,
             "ocr_confidence_component": 0.9, "attribute_match": 1.0,
             "camera_reliability_weight": 0.95, "match_confidence_label": "confirmed"},
            {"camera_id": "cam-B", "track_id": "t1", "fused_plate_text": "NORMAL",
             "fused_confidence": 0.92, "vehicle_type": "SUV", "vehicle_colour": "Blue",
             "captured_at": _ts(300), "identity_score": 0.93, "plate_similarity": 1.0,
             "ocr_confidence_component": 0.88, "attribute_match": 1.0,
             "camera_reliability_weight": 0.92, "match_confidence_label": "confirmed"},
        ]
        result = reconstruct_trajectory("NORMAL", obs, _TEST_GRAPH)
        assert result["anomaly_flags"] == []
        assert result["total_anomalies"] == 0
        assert all(not o["is_impossible_journey"] for o in result["observations"])

    def test_impossible_journey_flagged(self):
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "IJ",
             "fused_confidence": 0.9, "vehicle_type": "car", "vehicle_colour": "red",
             "captured_at": _ts(0), "identity_score": 0.9, "plate_similarity": 1.0,
             "ocr_confidence_component": 0.85, "attribute_match": 1.0,
             "camera_reliability_weight": 0.9, "match_confidence_label": "confirmed"},
            {"camera_id": "cam-C", "track_id": "t1", "fused_plate_text": "IJ",
             "fused_confidence": 0.88, "vehicle_type": "car", "vehicle_colour": "red",
             "captured_at": _ts(5), "identity_score": 0.88, "plate_similarity": 1.0,
             "ocr_confidence_component": 0.83, "attribute_match": 1.0,
             "camera_reliability_weight": 0.88, "match_confidence_label": "confirmed"},
        ]
        result = reconstruct_trajectory("IJ", obs, _TEST_GRAPH)
        assert "impossible_journey" in result["anomaly_flags"]
        assert result["total_anomalies"] >= 1
        flagged = [o for o in result["observations"] if o["is_impossible_journey"]]
        assert len(flagged) >= 1

    def test_all_observations_have_anomaly_type_field(self):
        obs = [
            {"camera_id": "cam-A", "track_id": "t1", "fused_plate_text": "P",
             "fused_confidence": 0.9, "vehicle_type": "car", "vehicle_colour": "blue",
             "captured_at": _ts(0), "identity_score": 0.9, "plate_similarity": 1.0,
             "ocr_confidence_component": 0.85, "attribute_match": 1.0,
             "camera_reliability_weight": 0.9, "match_confidence_label": "confirmed"},
        ]
        result = reconstruct_trajectory("P", obs, _TEST_GRAPH)
        for o in result["observations"]:
            assert "anomaly_type" in o
            assert "is_impossible_journey" in o


# ---------------------------------------------------------------------------
# 9. Staged QA scenarios from staged_scenarios.json
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _STAGED.exists(), reason="staged_scenarios.json not found")
class TestStagedScenarios:
    """Reproduce all 4 M4 QA scenarios using the road graph from seed data."""

    @pytest.fixture(autouse=True)
    def _load_scenarios(self):
        data = json.loads(_STAGED.read_text(encoding="utf-8"))
        self.scenarios = {s["id"]: s for s in data["scenarios"]}
        from app.modules.spatial_temporal.road_graph import build_road_graph
        self.graph = build_road_graph()  # real seed graph

    def _run(self, scenario_id: str) -> dict:
        s = self.scenarios[scenario_id]
        return reconstruct_trajectory(
            s["observations"][0]["fused_plate_text"],
            s["observations"],
            self.graph,
        )

    def test_scn_m4_01_normal_trajectory_no_anomalies(self):
        result = self._run("SCN-M4-01")
        expected = self.scenarios["SCN-M4-01"]["expected"]
        assert result["anomaly_flags"] == expected["anomaly_flags"]
        assert result["total_anomalies"] == expected["total_anomalies"]
        # Verify chronological order
        cams = [o["camera_id"] for o in result["observations"]]
        assert cams == expected["observations_in_order"]

    def test_scn_m4_02_impossible_journey(self):
        result = self._run("SCN-M4-02")
        assert "impossible_journey" in result["anomaly_flags"]
        assert result["total_anomalies"] >= 1
        impossible = [o for o in result["observations"] if o.get("is_impossible_journey")]
        assert len(impossible) >= 1

    def test_scn_m4_03_duplicate_plate(self):
        result = self._run("SCN-M4-03")
        assert "duplicate_plate" in result["anomaly_flags"]
        assert result["total_anomalies"] >= 1

    def test_scn_m4_04_camera_inconsistency(self):
        result = self._run("SCN-M4-04")
        assert "camera_inconsistency" in result["anomaly_flags"]
        assert result["total_anomalies"] >= 1


# ---------------------------------------------------------------------------
# 10. HTTP endpoint — anomaly fields in response
# ---------------------------------------------------------------------------

class TestTrajectoryEndpointM4:
    def test_response_has_anomaly_flags(self, api_client: TestClient, auth_token: str):
        resp = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert "anomaly_flags" in payload
        assert isinstance(payload["anomaly_flags"], list)

    def test_response_has_total_anomalies(self, api_client: TestClient, auth_token: str):
        resp = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        payload = resp.json()
        assert "total_anomalies" in payload
        assert isinstance(payload["total_anomalies"], int)

    def test_observations_have_is_impossible_journey(self, api_client: TestClient, auth_token: str):
        resp = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        for obs in resp.json()["observations"]:
            assert "is_impossible_journey" in obs

    def test_observations_have_anomaly_type(self, api_client: TestClient, auth_token: str):
        resp = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        for obs in resp.json()["observations"]:
            assert "anomaly_type" in obs
            # anomaly_type is None or a valid string
            val = obs["anomaly_type"]
            assert val is None or val in {"impossible_journey", "duplicate_plate", "camera_inconsistency"}

    def test_observations_still_have_m3_evidence(self, api_client: TestClient, auth_token: str):
        """M4 must not break M3 evidence fields."""
        resp = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        obs = resp.json()["observations"][0]
        assert "identity_score" in obs
        assert "match_confidence_label" in obs
        assert "evidence" in obs
        ev = obs["evidence"]
        assert "plate_similarity" in ev

    def test_anon_demo_still_works(self, api_client: TestClient):
        resp = api_client.get("/vehicles/TN%2037%20CY%201234/trajectory")
        assert resp.status_code == 200
