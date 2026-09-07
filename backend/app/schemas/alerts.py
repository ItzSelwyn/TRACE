from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class AlertResponse(BaseModel):
    alert_id: uuid.UUID
    type: str
    plate_text: str
    camera_id: uuid.UUID
    anomaly_id: Optional[uuid.UUID] = None
    blacklist_id: Optional[uuid.UUID] = None
    triggered_at: datetime
    reviewed: bool
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None

    # Enriched fields for frontend display
    camera_name: Optional[str] = None
    location: Optional[str] = None
    vehicle_type: Optional[str] = "CAR"
    vehicle_color: Optional[str] = "UNKNOWN"
    confidence: Optional[int] = 92
    scanned_timestamp: Optional[str] = None
    reason: Optional[str] = None
    category: Optional[str] = "BLACKLIST"
    status: Optional[str] = "UNVERIFIED"

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int
    verified_count: int = 0
    unverified_count: int = 0


class AlertReviewRequest(BaseModel):
    reviewed: bool

