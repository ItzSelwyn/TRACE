from pathlib import Path

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.db.models import User
from app.modules.perception import load_ground_truth_by_camera, process_all_cameras

router = APIRouter()

DEFAULT_CAMERA_IDS = ["c020", "c023", "c029", "c035"]
DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "ground_truth" / "cityflow_train_gt.jsonl"


@router.get("/perception/status")
async def get_perception_status(current_user: User = Depends(get_current_user)):
    """Return the current camera-level perception status from the local ground-truth feed."""
    dataset_records = load_ground_truth_by_camera(DATASET_PATH, camera_ids=DEFAULT_CAMERA_IDS)
    camera_results = process_all_cameras(DEFAULT_CAMERA_IDS, dataset_records=dataset_records)
    return {
        "status": "ok",
        "camera_count": len(camera_results),
        "cameras": camera_results,
        "source": str(DATASET_PATH),
    }
