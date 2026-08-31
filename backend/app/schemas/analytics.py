from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

class HeatmapSegment(BaseModel):
    edge_id: uuid.UUID
    from_camera_id: uuid.UUID
    to_camera_id: uuid.UUID
    density: int
    congestion_status: str
    avg_speed_kmph: float

    model_config = {"from_attributes": True}

class HeatmapResponse(BaseModel):
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    segments: List[HeatmapSegment]

class ODEntry(BaseModel):
    origin_zone: str
    destination_zone: str
    trip_count: int

    model_config = {"from_attributes": True}

class ODMatrixResponse(BaseModel):
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    entries: List[ODEntry]

class SegmentDetailResponse(BaseModel):
    edge_id: uuid.UUID
    from_camera_id: uuid.UUID
    to_camera_id: uuid.UUID
    density: int
    avg_speed_kmph: float
    congestion_status: str
    speed_limit_kmph: Optional[int] = None
    distance_km: Optional[float] = None

    model_config = {"from_attributes": True}

class ForecastResponse(BaseModel):
    edge_id: uuid.UUID
    forecast_for_window: datetime
    predicted_density: int
    congestion_probability: float
    generated_at: datetime

    model_config = {"from_attributes": True}
