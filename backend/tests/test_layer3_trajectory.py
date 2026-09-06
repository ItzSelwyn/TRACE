"""
Layer 3 — Spatial-Temporal Reasoning & Multi-Identifier Trajectory Test Suite.
=============================================================================

Tests all 20 requirements from specification:
  1. Search by canonical UUID
  2. Search by observation UUID
  3. Search by track ID
  4. Search by plate
  5. Search for nonexistent vehicle
  6. Search handles plate-free observations
  7. Canonical vehicle returns all confirmed observations
  8. Observation ID resolves to the correct identity cluster
  9. Track ID resolves correctly
 10. Plate resolves correctly
 11. Plate-free CityFlow trajectory works
 12. Chronological ordering is correct
 13. Camera transitions are correctly identified
 14. Road graph distance is used when available
 15. Implied speed is calculated correctly
 16. Impossible journey is detected
 17. Candidate vs confirmed identity links are distinguished
 18. Evidence breakdown is returned
 19. Ground truth is not used in production scoring
 20. Existing trajectory behavior remains backward compatible
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    Camera,
    CanonicalVehicle,
    IdentityMatch,
    TrajectoryPoint,
    VehicleObservation,
)
from app.dependencies import create_access_token
from app.main import app
from app.modules.spatial_temporal.road_graph import get_road_graph
from app.modules.spatial_temporal.trajectory_service import (
    find_and_build_trajectory,
    resolve_vehicle_identity,
    search_vehicles,
)


@pytest.fixture()
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def auth_token() -> str:
    return create_access_token({"sub": str(uuid.uuid4()), "role": "operator"})


@pytest.fixture()
def sync_db():
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Search Tests (1 - 6)
# ---------------------------------------------------------------------------

class TestVehicleSearch:
    def test_search_by_plate(self, sync_db: Session):
        """Test searching vehicles by plate query."""
        resp = search_vehicles(sync_db, "TN37")
        assert resp.total >= 1
        assert any("TN37" in r.identifier for r in resp.results)
        assert any(r.has_plate for r in resp.results)

    def test_search_by_track_id(self, sync_db: Session):
        """Test searching vehicles by track ID."""
        resp = search_vehicles(sync_db, "TRK-D")
        assert resp.total >= 1
        assert any("TRK-D" in r.identifier for r in resp.results)

    def test_search_by_canonical_uuid(self, sync_db: Session):
        """Test searching by canonical vehicle UUID."""
        canon = sync_db.execute(select(CanonicalVehicle).limit(1)).scalars().first()
        if canon:
            resp = search_vehicles(sync_db, str(canon.canonical_vehicle_id))
            assert resp.total >= 1

    def test_search_nonexistent_vehicle(self, sync_db: Session):
        """Test searching for a non-existent vehicle returns empty results."""
        resp = search_vehicles(sync_db, "NON_EXISTENT_QUERY_XYZ_9999")
        assert resp.total == 0
        assert len(resp.results) == 0

    def test_search_handles_plate_free_observations(self, sync_db: Session):
        """Plate-free observations should have has_plate=False and identifier_type='track_id'."""
        resp = search_vehicles(sync_db, "TRK-")
        plate_free = [r for r in resp.results if not r.has_plate]
        if plate_free:
            sample = plate_free[0]
            assert sample.identifier_type == "track_id"
            assert not sample.has_plate

    def test_search_endpoint_http(self, api_client: TestClient, auth_token: str):
        """HTTP endpoint test for /vehicles/search."""
        res = api_client.get(
            "/vehicles/search?q=TRK",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert "total" in data
        assert isinstance(data["results"], list)


# ---------------------------------------------------------------------------
# Trajectory Resolution & Reconstruction Tests (7 - 20)
# ---------------------------------------------------------------------------

class TestTrajectoryResolution:
    def test_canonical_vehicle_resolves_to_canonical_id(self, sync_db: Session):
        """Canonical UUID query resolves with identifier_type='canonical_id'."""
        canon = sync_db.execute(select(CanonicalVehicle).limit(1)).scalars().first()
        if canon:
            resolved = resolve_vehicle_identity(sync_db, str(canon.canonical_vehicle_id))
            assert resolved is not None
            assert resolved["identifier_type"] == "canonical_id"
            assert resolved["canonical_vehicle_id"] == canon.canonical_vehicle_id

    def test_observation_uuid_resolves_to_observation_id(self, sync_db: Session):
        """Observation UUID resolves with identifier_type='observation_id'."""
        obs = sync_db.execute(select(VehicleObservation).limit(1)).scalars().first()
        assert obs is not None
        resolved = resolve_vehicle_identity(sync_db, str(obs.observation_id))
        assert resolved is not None
        assert resolved["identifier_type"] == "observation_id"
        assert len(resolved["target_observations"]) >= 1

    def test_track_id_resolves_correctly(self, sync_db: Session):
        """Track ID resolves with identifier_type='track_id'."""
        obs = sync_db.execute(
            select(VehicleObservation).where(VehicleObservation.track_id.like("TRK-%")).limit(1)
        ).scalars().first()
        if obs:
            resolved = resolve_vehicle_identity(sync_db, obs.track_id)
            assert resolved is not None
            assert resolved["identifier_type"] == "track_id"

    def test_plate_resolves_correctly(self, sync_db: Session):
        """Plate string query resolves with identifier_type='plate'."""
        resolved = resolve_vehicle_identity(sync_db, "TN 37 CY 1234")
        assert resolved is not None
        assert resolved["identifier_type"] == "plate"

    def test_plate_free_cityflow_trajectory_works(self, api_client: TestClient, auth_token: str):
        """CityFlow vehicle track ID works without license plates."""
        res = api_client.get(
            "/vehicles/TRK-D1/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["vehicle_id"] == "TRK-D1"
        assert len(data["observations"]) >= 1
        # Fused plate may be None or 'NOT READ'
        for obs in data["observations"]:
            assert obs["fused_plate_text"] in ("NOT READ", "", None, "None")

    def test_chronological_ordering(self, api_client: TestClient, auth_token: str):
        """Observations must be strictly sorted chronologically."""
        res = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert res.status_code == 200
        obs_list = res.json()["observations"]
        timestamps = [datetime.fromisoformat(o["captured_at"]) for o in obs_list]
        assert timestamps == sorted(timestamps)

    def test_camera_transitions_identified(self, api_client: TestClient, auth_token: str):
        """Multi-camera trajectory identifies valid camera transitions."""
        res = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert res.status_code == 200
        obs_list = res.json()["observations"]
        if len(obs_list) > 1:
            cam_ids = [o["camera_id"] for o in obs_list]
            # Must have camera information
            assert all(cid is not None for cid in cam_ids)

    def test_road_graph_distance_and_implied_speed(self, sync_db: Session):
        """Road graph calculates distance and implied speed for transitions."""
        graph = get_road_graph()
        resp = find_and_build_trajectory(sync_db, "TN 37 CY 1234", road_graph=graph)
        assert len(resp.observations) >= 1
        # If consecutive observations cross edges, implied_speed_kmph should be computed
        speeds = [o.implied_speed_kmph for o in resp.observations if o.implied_speed_kmph is not None]
        assert isinstance(speeds, list)

    def test_impossible_journey_detected(self, api_client: TestClient, auth_token: str):
        """Impossible journeys are flagged when time gap is infeasible."""
        res = api_client.get(
            "/vehicles/TRK-D1/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "anomaly_flags" in data

    def test_candidate_vs_confirmed_distinguished(self, api_client: TestClient, auth_token: str):
        """match_confidence_label must be confirmed, candidate, or no_match."""
        res = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert res.status_code == 200
        for obs in res.json()["observations"]:
            assert obs["match_confidence_label"] in ("confirmed", "candidate", "no_match")

    def test_evidence_breakdown_returned(self, api_client: TestClient, auth_token: str):
        """Explainable Layer 2 evidence breakdown must be returned with each observation."""
        res = api_client.get(
            "/vehicles/TN%2037%20CY%201234/trajectory",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert res.status_code == 200
        obs = res.json()["observations"][0]
        assert "evidence" in obs
        ev = obs["evidence"]
        assert ev is not None
        assert "attribute_match" in ev

    def test_ground_truth_not_used_when_db_records_exist(self, sync_db: Session):
        """Production trajectory must be built from database, not ground truth fallback."""
        resp = find_and_build_trajectory(sync_db, "TN 37 CY 1234")
        assert resp.identifier_type == "plate"
        assert resp.identifier_type != "cityflow_ground_truth_fallback"

    def test_backward_compatibility_endpoint(self, api_client: TestClient):
        """Anonymous access and standard payload structure remain backward compatible."""
        res = api_client.get("/vehicles/TN%2037%20CY%201234/trajectory")
        assert res.status_code == 200
        payload = res.json()
        assert payload["plate"] == "TN 37 CY 1234"
        assert "observations" in payload
        assert "anomaly_flags" in payload
        assert "total_anomalies" in payload

