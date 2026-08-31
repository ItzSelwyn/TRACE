from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends

from app.schemas.alerts import AlertListResponse, AlertReviewRequest, AlertResponse
from app.dependencies import get_current_user, require_role
from app.db.models import User

router = APIRouter()


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(current_user: User = Depends(get_current_user)):
    """M1 scaffold: return an empty but valid alert list."""
    return AlertListResponse(alerts=[], total=0)


@router.patch("/alerts/{id}", response_model=AlertResponse)
async def update_alert(
    id: uuid.UUID,
    review: AlertReviewRequest,
    current_user: User = Depends(require_role("operator", "admin")),
):
    """M1 scaffold: accept the review payload and persist the placeholder response."""
    now = datetime.now(timezone.utc)
    return AlertResponse(
        alert_id=id,
        type="blacklist_hit",
        plate_text="ABC123",
        camera_id=uuid.uuid4(),
        anomaly_id=None,
        blacklist_id=None,
        triggered_at=now,
        reviewed=review.reviewed,
        reviewed_by=current_user.user_id,
        reviewed_at=now if review.reviewed else None,
    )
