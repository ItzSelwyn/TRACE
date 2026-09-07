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

class CameraTrafficStat(BaseModel):
    camera_id: str
    name: str
    short_name: Optional[str] = None
    location: str
    latitude: float
    longitude: float
    vehicle_count: int
    traffic_density: float
    congestion_level: str
    weight: float
    status_color: Optional[str] = "green"
    max_capacity: Optional[int] = 200

class HeatmapCoordinate(BaseModel):
    lng: float
    lat: float
    weight: float

class HeatmapResponse(BaseModel):
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    segments: List[HeatmapSegment] = []
    corridor_name: Optional[str] = "Grandview & Highway 20 Corridor"
    subtitle: Optional[str] = None
    cameras_label: Optional[str] = "Camera 020, Camera 023, Camera 029, Camera 035"
    total_vehicles: int = 0
    max_capacity: int = 480
    congestion_index: str = "Critical"
    camera_stats: List[CameraTrafficStat] = []
    heatmap_points: List[HeatmapCoordinate] = []

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
