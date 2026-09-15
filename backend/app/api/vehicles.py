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

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_sync_db
from app.dependencies import get_current_user
from app.modules.spatial_temporal.road_graph import get_road_graph
from app.modules.spatial_temporal.trajectory_service import (
    find_and_build_trajectory,
    get_active_cross_camera_paths,
    search_vehicles,
)
from app.schemas.vehicles import (
    CrossCameraPathsResponse,
    TrajectoryResponse,
    VehicleSearchResponse,
)

router = APIRouter()


@router.get("/vehicles/cross-camera-paths", response_model=CrossCameraPathsResponse)
def list_cross_camera_paths(
    limit: int = Query(10, description="Max cross-camera paths to return"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_sync_db),
):
    """Return dynamically discovered cross-camera paths from the active corridor scenario."""
    paths = get_active_cross_camera_paths(session, limit=limit)
    return CrossCameraPathsResponse(status="ok", total=len(paths), paths=paths)


@router.get("/vehicles/search", response_model=VehicleSearchResponse)
def search_vehicle_records(
    q: str = Query("", description="Plate, Track ID, or Canonical UUID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_sync_db),
):
    """Search vehicles in PostgreSQL across track IDs, canonical vehicles, and license plates."""
    return search_vehicles(session, q)


@router.get("/vehicles/{query}/trajectory", response_model=TrajectoryResponse)
def get_trajectory(
    query: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_sync_db),
):
    """Return a fully annotated vehicle trajectory.

    Resolves:
    - License plate (e.g. 'TN 37 CY 1234')
    - Track ID (e.g. 'TRK-001', 'TRK-D1')
    - Canonical Vehicle UUID
    - Observation UUID

    Prioritizes PostgreSQL database records first; uses offline GT fallback
    strictly when no database record matches the query.
    """
    return find_and_build_trajectory(session, query, road_graph=get_road_graph())

