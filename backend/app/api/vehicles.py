"""
Vehicles API — trajectory endpoint with M3 identity fusion + M4 spatial-temporal reasoning.

Pipeline per request:
  1. Load GT records from CityFlow JSONL (Layer 1 — perception data source)
  2. Run identity fusion: build_vehicle_trajectory() [Layer 2]
  3. Enrich observations with camera lat/lon from seed data
  4. Run spatial-temporal reconstruction: reconstruct_trajectory() [Layer 3]
     → chronological sort, impossible-journey detection, dup-plate, cam-inconsistency
  5. Map into Pydantic response with full evidence + anomaly fields

Camera reliability profiles and road graph are loaded from seed JSON files at
startup (no DB call — NFR-08 module independence).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.db.models import User
from app.modules.identity import build_vehicle_trajectory
from app.modules.perception import load_ground_truth_by_camera
from app.modules.spatial_temporal import reconstruct_trajectory
from app.modules.spatial_temporal.road_graph import get_road_graph
from app.schemas.vehicles import EvidenceBreakdown, ObservationInTrajectory, TrajectoryResponse

router = APIRouter()

# Hardcode paths for now, can be refactored later
_HARDCODED_ROOT = r"D:\coding\TRACE"
_PROJECT_ROOT = Path(_HARDCODED_ROOT) if Path(_HARDCODED_ROOT).exists() else Path(__file__).resolve().parents[4]
DATASET_PATH = _PROJECT_ROOT / "data" / "ground_truth" / "cityflow_train_gt.jsonl"
CAMERAS_SEED_PATH = _PROJECT_ROOT / "data" / "seed" / "cameras.json"


def _load_camera_profiles() -> dict[str, dict]:
    """Load camera reliability profiles keyed by camera_id."""
    if not CAMERAS_SEED_PATH.exists():
        return {}
    try:
        cameras = json.loads(CAMERAS_SEED_PATH.read_text(encoding="utf-8"))
        return {cam["camera_id"]: cam["reliability"] for cam in cameras if "reliability" in cam}
    except Exception:
        return {}


def _load_camera_locations() -> dict[str, dict]:
    """Load camera lat/lon keyed by camera_id."""
    if not CAMERAS_SEED_PATH.exists():
        return {}
    try:
        cameras = json.loads(CAMERAS_SEED_PATH.read_text(encoding="utf-8"))
        return {
            cam["camera_id"]: {
                "name": cam.get("name", cam["camera_id"]),
                "latitude": cam.get("latitude"),
                "longitude": cam.get("longitude"),
            }
            for cam in cameras
        }
    except Exception:
        return {}


# Eagerly loaded at import time — static seed data
_CAMERA_PROFILES: dict[str, dict] = _load_camera_profiles()
_CAMERA_LOCATIONS: dict[str, dict] = _load_camera_locations()


@router.get("/vehicles/{plate}/trajectory", response_model=TrajectoryResponse)
async def get_trajectory(plate: str, current_user: User = Depends(get_current_user)):
    """Return a fully annotated vehicle trajectory.

    Each observation includes:
    - identity_score + evidence breakdown (Layer 2, M3)
    - match_confidence_label: 'confirmed' / 'candidate' / 'no_match'
    - is_impossible_journey, implied_speed_kmph, anomaly_type (Layer 3, M4)
    - Trajectory is sorted chronologically; anomaly_flags lists all anomaly
      types present across the journey.
    """
    # --- Layer 1: Load perception records ---------------------------------
    dataset_records = load_ground_truth_by_camera(DATASET_PATH)
    selected_records: list[dict] = []
    for camera_records in dataset_records.values():
        selected_records.extend(camera_records[:25])

    # --- Layer 2: Identity fusion ----------------------------------------
    identity_payload = build_vehicle_trajectory(
        plate,
        selected_records or None,
        camera_profiles=_CAMERA_PROFILES,
    )
    raw_observations = identity_payload["observations"]

    # Enrich with camera lat/lon from seed (GT cameras like c020 won't match
    # Bangalore seed cameras — that's expected; lat/lon stays None until M5
    # wires real spatial data from the DB)
    for obs in raw_observations:
        cam_id = str(obs.get("camera_id", ""))
        loc = _CAMERA_LOCATIONS.get(cam_id, {})
        if loc:
            obs["latitude"] = loc.get("latitude")
            obs["longitude"] = loc.get("longitude")
            obs["camera_name"] = loc.get("name", obs.get("camera_name"))

    # --- Layer 3: Spatial-temporal reconstruction ------------------------
    graph = get_road_graph()
    spatial_payload = reconstruct_trajectory(plate, raw_observations, graph)
    annotated_obs = spatial_payload["observations"]

    # --- Map to Pydantic response ----------------------------------------
    observations = []
    for obs in annotated_obs:
        evidence = EvidenceBreakdown(
            plate_similarity=obs.get("plate_similarity", 1.0),
            ocr_confidence_component=obs.get("ocr_confidence_component", 0.90),
            attribute_match=obs.get("attribute_match", 1.0),
            camera_reliability_weight=obs.get("camera_reliability_weight", 0.90),
        )
        observations.append(
            ObservationInTrajectory(
                observation_id=uuid4(),
                camera_id=uuid4(),
                camera_name=obs.get("camera_name"),
                captured_at=datetime.fromisoformat(obs["captured_at"]),
                fused_plate_text=obs["fused_plate_text"],
                fused_confidence=float(obs["fused_confidence"]),
                vehicle_type=obs.get("vehicle_type", "vehicle"),
                vehicle_colour=obs.get("vehicle_colour", "unknown"),
                identity_score=float(obs["identity_score"]),
                match_confidence_label=obs.get("match_confidence_label"),
                evidence=evidence,
                is_impossible_journey=bool(obs.get("is_impossible_journey", False)),
                implied_speed_kmph=obs.get("implied_speed_kmph"),
                anomaly_type=obs.get("anomaly_type"),
                latitude=obs.get("latitude"),
                longitude=obs.get("longitude"),
            )
        )

    return TrajectoryResponse(
        plate=plate,
        observations=observations,
        anomaly_flags=spatial_payload.get("anomaly_flags", []),
        total_anomalies=spatial_payload.get("total_anomalies", 0),
    )
