from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.db.models import User
from app.schemas.vehicles import TrajectoryResponse, ObservationInTrajectory

router = APIRouter()


@router.get("/vehicles/{plate}/trajectory", response_model=TrajectoryResponse)
async def get_trajectory(plate: str, current_user: User = Depends(get_current_user)):
    """M1 scaffold: return an empty but correctly shaped trajectory result."""
    return TrajectoryResponse(
        plate=plate,
        observations=[
            ObservationInTrajectory(
                observation_id=uuid4(),
                camera_id=uuid4(),
                camera_name="demo-camera",
                captured_at=datetime.now(timezone.utc),
                fused_plate_text=plate,
                fused_confidence=0.0,
                vehicle_type="car",
                vehicle_colour="unknown",
                identity_score=0.0,
                is_impossible_journey=False,
                latitude=0.0,
                longitude=0.0,
            )
        ] if False else None
    )
