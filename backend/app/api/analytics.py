from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends

from app.schemas.analytics import HeatmapResponse, ODMatrixResponse, SegmentDetailResponse, ForecastResponse
from app.dependencies import get_current_user
from app.db.models import User

router = APIRouter()


@router.get("/analytics/heatmap", response_model=HeatmapResponse)
async def get_heatmap(current_user: User = Depends(get_current_user)):
    """M1 scaffold: return an empty but valid heatmap payload."""
    return HeatmapResponse(
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        segments=[],
    )


@router.get("/analytics/od-matrix", response_model=ODMatrixResponse)
async def get_od_matrix(current_user: User = Depends(get_current_user)):
    """M1 scaffold: return an empty OD matrix payload."""
    return ODMatrixResponse(
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        entries=[],
    )


@router.get("/analytics/segments/{id}", response_model=SegmentDetailResponse)
async def get_segment(id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """M1 scaffold: return a valid placeholder detail object."""
    return SegmentDetailResponse(
        edge_id=id,
        from_camera_id=uuid.uuid4(),
        to_camera_id=uuid.uuid4(),
        density=0,
        avg_speed_kmph=0.0,
        congestion_status="free",
        speed_limit_kmph=0,
        distance_km=0.0,
    )


@router.get("/analytics/forecast/{segment_id}", response_model=ForecastResponse)
async def get_forecast(segment_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """M1 scaffold: return a valid placeholder forecast object."""
    now = datetime.now(timezone.utc)
    return ForecastResponse(
        edge_id=segment_id,
        forecast_for_window=now,
        predicted_density=0,
        congestion_probability=0.0,
        generated_at=now,
    )
