from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, status

from app.schemas.blacklist import BlacklistListResponse, BlacklistEntryCreate, BlacklistEntryResponse
from app.dependencies import get_current_user, require_role
from app.db.models import User

router = APIRouter()


@router.get("/blacklist", response_model=BlacklistListResponse)
async def get_blacklist(current_user: User = Depends(get_current_user)):
    """M1 scaffold: return an empty but valid blacklist collection."""
    return BlacklistListResponse(entries=[], total=0)


@router.post("/blacklist", response_model=BlacklistEntryResponse, status_code=status.HTTP_201_CREATED)
async def add_blacklist(
    entry: BlacklistEntryCreate,
    current_user: User = Depends(require_role("admin")),
):
    """M1 scaffold: accept the blacklist payload and return the created record."""
    now = datetime.now(timezone.utc)
    return BlacklistEntryResponse(
        blacklist_id=uuid4(),
        plate_text=entry.plate_text,
        reason=entry.reason,
        added_by=current_user.user_id,
        added_at=now,
        active=True,
    )
