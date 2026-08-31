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

    model_config = {"from_attributes": True}

class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int

class AlertReviewRequest(BaseModel):
    reviewed: bool
