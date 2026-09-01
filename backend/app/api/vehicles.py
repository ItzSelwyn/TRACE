"""
Vehicles API — trajectory endpoint with real M3 identity fusion.

Camera reliability profiles are loaded from the seed JSON at startup so the
identity engine can weight OCR confidence appropriately without a database call.
This is intentional for M3: the module layer is pure-Python (NFR-08) and the DB
integration is deferred to M4 when trajectory_points are persisted.
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
from app.schemas.vehicles import EvidenceBreakdown, ObservationInTrajectory, TrajectoryResponse

router = APIRouter()

# Path constants — both relative to the project root
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = _BACKEND_ROOT / "data" / "ground_truth" / "cityflow_train_gt.jsonl"
CAMERAS_SEED_PATH = _BACKEND_ROOT / "data" / "seed" / "cameras.json"


def _load_camera_profiles() -> dict[str, dict[str, float]]:
    """Load camera reliability profiles keyed by camera_id from the seed JSON.

    Returns an empty dict if the seed file is missing (graceful degradation).
    Each profile has keys: day_ocr_reliability, night_ocr_reliability,
    rain_ocr_reliability, angle_ocr_reliability.
    """
    if not CAMERAS_SEED_PATH.exists():
        return {}
    try:
        cameras = json.loads(CAMERAS_SEED_PATH.read_text(encoding="utf-8"))
        return {
            cam["camera_id"]: cam["reliability"]
            for cam in cameras
            if "reliability" in cam
        }
    except Exception:
        return {}


# Eagerly load at import time — file is small and static for M3
_CAMERA_PROFILES: dict[str, dict[str, float]] = _load_camera_profiles()


@router.get("/vehicles/{plate}/trajectory", response_model=TrajectoryResponse)
async def get_trajectory(plate: str, current_user: User = Depends(get_current_user)):
    """Return a vehicle trajectory with full identity evidence breakdown.

    Uses ground-truth records from the repo's CityFlow JSONL as the observation
    source. Each observation includes:
    - identity_score: composite M3 score
    - match_confidence_label: 'confirmed' / 'candidate' / 'no_match'
    - evidence: plate_similarity, ocr_confidence_component, attribute_match,
                camera_reliability_weight
    """
    # Load GT records from all available cameras
    dataset_records = load_ground_truth_by_camera(DATASET_PATH)
    selected_records: list[dict] = []
    for camera_records in dataset_records.values():
        selected_records.extend(camera_records[:25])

    # Run identity fusion
    payload = build_vehicle_trajectory(
        plate,
        selected_records or None,
        camera_profiles=_CAMERA_PROFILES,
    )

    # Map into Pydantic response models
    observations = []
    for obs in payload["observations"]:
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
                is_impossible_journey=bool(obs.get("is_impossible_journey", False)),
                evidence=evidence,
                latitude=obs.get("latitude"),
                longitude=obs.get("longitude"),
            )
        )

    return TrajectoryResponse(plate=plate, observations=observations)
