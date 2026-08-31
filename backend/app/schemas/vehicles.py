from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class ObservationInTrajectory(BaseModel):
    observation_id: uuid.UUID
    camera_id: uuid.UUID
    camera_name: Optional[str] = None
    captured_at: datetime
    fused_plate_text: str
    fused_confidence: float
    vehicle_type: str
    vehicle_colour: str
    identity_score: Optional[float] = None
    is_impossible_journey: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}

class TrajectoryResponse(BaseModel):
    plate: str
    observations: List[ObservationInTrajectory]
