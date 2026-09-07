from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class BlacklistEntryCreate(BaseModel):
    plate_text: str
    reason: str


class BlacklistEntryResponse(BaseModel):
    blacklist_id: uuid.UUID
    plate_text: str
    reason: str
    added_by: uuid.UUID
    added_at: datetime
    active: bool
    last_found: Optional[str] = None
    last_camera_name: Optional[str] = None
    last_location: Optional[str] = None
    date_added_formatted: Optional[str] = None
    time_added_formatted: Optional[str] = None

    model_config = {"from_attributes": True}


class BlacklistListResponse(BaseModel):
    entries: List[BlacklistEntryResponse]
    total: int

