"""Layer 1 — Perception Module: Central Dataset Profiles & Configuration for S04, S05, and CBE."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("trace.perception.dataset_profiles")

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
ACTIVE_DATASET_FILE = "active_dataset.json"

# Central Dataset Profiles Definition
DATASET_PROFILES: Dict[str, Dict[str, Any]] = {
    "S04": {
        "id": "S04",
        "label": "CityFlow S04",
        "footage_dir": "footage/S04",
        "map_profile": "cityflow",
        "description": "CityFlow Challenge Corridor S04 (Dubuque, Iowa)",
        "cameras": {
            "c020": {
                "name": "Camera 020 (University Ave & Walnut)",
                "location": "University Ave & Walnut",
                "source_path": "footage/S04/c020/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.499860,
                "longitude": -90.675620,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c023": {
                "name": "Camera 023 (University Ave & Nevada)",
                "location": "University Ave & Nevada",
                "source_path": "footage/S04/c023/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.499140,
                "longitude": -90.681350,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c028": {
                "name": "Camera 028 (Grandview Roundabout)",
                "location": "Grandview Roundabout",
                "source_path": "footage/S04/c028/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.498360,
                "longitude": -90.688350,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c029": {
                "name": "Camera 029 (University Ave & Alta Pl)",
                "location": "University Ave & Alta Pl",
                "source_path": "footage/S04/c029/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.499190,
                "longitude": -90.693500,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
        },
    },
    "S05": {
        "id": "S05",
        "label": "CityFlow S05",
        "footage_dir": "footage/S05",
        "map_profile": "cityflow",
        "description": "CityFlow Challenge Corridor S05 (Dubuque, Iowa)",
        "cameras": {
            "c020": {
                "name": "Camera 020 (University Ave & Walnut)",
                "location": "University Ave & Walnut",
                "source_path": "footage/S05/c020/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.499860,
                "longitude": -90.675620,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c023": {
                "name": "Camera 023 (University Ave & Nevada)",
                "location": "University Ave & Nevada",
                "source_path": "footage/S05/c023/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.499140,
                "longitude": -90.681350,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c028": {
                "name": "Camera 028 (Grandview Roundabout)",
                "location": "Grandview Roundabout",
                "source_path": "footage/S05/c028/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.498360,
                "longitude": -90.688350,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c029": {
                "name": "Camera 029 (University Ave & Alta Pl)",
                "location": "University Ave & Alta Pl",
                "source_path": "footage/S05/c029/vdo.avi",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 42.499190,
                "longitude": -90.693500,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
        },
    },
    "CBE": {
        "id": "CBE",
        "label": "Coimbatore CBE",
        "footage_dir": "footage/CBE",
        "map_profile": "coimbatore",
        "description": "Coimbatore Corridor near SKCET, Kuniyamuthur (Palghat Rd & Kovaipudur Rd)",
        "cameras": {
            "c020": {
                "name": "Camera 020 (Palghat Rd North)",
                "location": "Palghat Rd North",
                "source_path": "footage/CBE/c020.mp4",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 10.948600,
                "longitude": 76.953400,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c023": {
                "name": "Camera 023 (Palghat Rd Junction)",
                "location": "Palghat Rd Junction",
                "source_path": "footage/CBE/c023.mp4",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 10.936340,
                "longitude": 76.951040,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c028": {
                "name": "Camera 028 (Palghat Rd South)",
                "location": "Palghat Rd South",
                "source_path": "footage/CBE/c028.MOV",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 10.930850,
                "longitude": 76.949610,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
            "c029": {
                "name": "Camera 029 (Kovaipudur Rd)",
                "location": "Kovaipudur Rd",
                "source_path": "footage/CBE/c029.mp4",
                "source_type": "video",
                "fps": 10.0,
                "latitude": 10.939600,
                "longitude": 76.945400,
                "resolution": "1080P",
                "sync_offset_s": 0.0,
            },
        },
    },
}

REQUIRED_CAMERAS = ["c020", "c023", "c028", "c029"]


def _get_active_dataset_path() -> Path:
    """Return the path to active_dataset.json in data/ directory."""
    from app.modules.perception.source_discovery import _get_project_data_dir
    return _get_project_data_dir() / ACTIVE_DATASET_FILE


def get_active_dataset_key() -> str:
    """Read the persistently stored active dataset key, defaulting to 'S05'."""
    path = _get_active_dataset_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                ds = data.get("active_dataset")
                if ds in DATASET_PROFILES:
                    return ds
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
    return "S05"


def set_active_dataset_key(dataset_key: str) -> None:
    """Persist the active dataset key to data/active_dataset.json."""
    if dataset_key not in DATASET_PROFILES:
        raise ValueError(f"Unknown dataset '{dataset_key}'")
    path = _get_active_dataset_path()
    try:
        data = {
            "active_dataset": dataset_key,
            "label": DATASET_PROFILES[dataset_key]["label"],
            "map_profile": DATASET_PROFILES[dataset_key]["map_profile"],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write active dataset to {path}: {e}")


def get_dataset_profile(dataset_key: str) -> Dict[str, Any]:
    """Retrieve full configuration profile for the requested dataset."""
    key = dataset_key.upper().strip()
    if key not in DATASET_PROFILES:
        raise ValueError(f"Dataset profile '{dataset_key}' not found. Available: {list(DATASET_PROFILES.keys())}")
    return DATASET_PROFILES[key]


def list_available_datasets() -> List[Dict[str, str]]:
    """Return concise list of available datasets for selector UI."""
    return [
        {"id": key, "label": profile["label"]}
        for key, profile in DATASET_PROFILES.items()
    ]


def validate_dataset_footage(dataset_key: str) -> Dict[str, Path]:
    """Validate that all four camera video files exist for the dataset.
    
    Returns:
        Dict[camera_id, Path] with resolved absolute file paths.
    Raises:
        FileNotFoundError if any camera video file is missing.
    """
    from app.modules.perception.source_discovery import _get_project_data_dir

    profile = get_dataset_profile(dataset_key)
    data_dir = _get_project_data_dir()
    resolved_paths: Dict[str, Path] = {}

    for cam_id in REQUIRED_CAMERAS:
        cam_info = profile["cameras"].get(cam_id)
        if not cam_info:
            raise ValueError(f"Missing camera definition for '{cam_id}' in dataset '{dataset_key}'")

        rel_path = cam_info["source_path"]
        cand1 = data_dir / rel_path
        if cand1.exists():
            resolved_paths[cam_id] = cand1
            continue

        cand2 = Path(rel_path)
        if cand2.is_absolute() and cand2.exists():
            resolved_paths[cam_id] = cand2
            continue

        cand3 = data_dir / "footage" / rel_path
        if cand3.exists():
            resolved_paths[cam_id] = cand3
            continue

        raise FileNotFoundError(
            f"Required footage for camera '{cam_id}' in dataset '{dataset_key}' not found: '{rel_path}' (checked {cand1})"
        )

    return resolved_paths
