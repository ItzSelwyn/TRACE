"""Layer 1 — Perception Module: Dynamic Source Discovery & CityFlow Synchronization Metadata Scanner."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

logger = logging.getLogger("trace.perception.source_discovery")

# Supported file extensions
VIDEO_EXTENSIONS = {".avi", ".mp4", ".mkv", ".mov"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _get_project_data_dir() -> Path:
    """Resolve the root data directory reliably."""
    # backend/app/modules/perception/source_discovery.py -> parents[4] is TRACE/
    root = Path(__file__).resolve().parents[4]
    candidates = [
        root / "data",
        Path.cwd() / "data",
        Path.cwd().parent / "data",
        Path("D:/coding/TRACE/data"),
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return root / "data"


def load_cityflow_sync_metadata(data_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Parse CityFlow camera start timestamps and frame counts from metadata files.
    
    Metadata locations:
    - data/footage/cam_timestamp/<scenario>.txt (start timestamps in seconds)
    - data/footage/cam_framenum/<scenario>.txt (total video frames)
    
    Returns:
        Dict[scenario_id, Dict[camera_id, {"start_timestamp_s": float, "frame_count": int}]]
    """
    base_dir = data_dir or _get_project_data_dir()
    ts_dir = base_dir / "footage" / "cam_timestamp"
    fn_dir = base_dir / "footage" / "cam_framenum"

    scenarios: Dict[str, Dict[str, Any]] = {}

    if not ts_dir.exists():
        return scenarios

    for ts_file in ts_dir.glob("*.txt"):
        scenario_name = ts_file.stem  # e.g. "S04"
        scenario_data: Dict[str, Any] = {}

        # 1. Read start timestamps
        try:
            with open(ts_file, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        cam_id = parts[0].strip().lower()
                        try:
                            start_s = float(parts[1].strip())
                            scenario_data[cam_id] = {
                                "start_timestamp_s": start_s,
                                "frame_count": None,
                            }
                        except ValueError:
                            continue
        except Exception as e:
            logger.warning(f"Failed to read {ts_file}: {e}")

        # 2. Read frame counts if available
        fn_file = fn_dir / f"{scenario_name}.txt"
        if fn_file.exists():
            try:
                with open(fn_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            cam_id = parts[0].strip().lower()
                            try:
                                total_frames = int(parts[1].strip())
                                if cam_id in scenario_data:
                                    scenario_data[cam_id]["frame_count"] = total_frames
                                else:
                                    scenario_data[cam_id] = {
                                        "start_timestamp_s": 0.0,
                                        "frame_count": total_frames,
                                    }
                            except ValueError:
                                continue
            except Exception as e:
                logger.warning(f"Failed to read {fn_file}: {e}")

        scenarios[scenario_name] = scenario_data

    return scenarios


def discover_sources(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Scan data/ and dynamically identify all available video and image sources with metadata.
    
    Returns:
        {
            "videos": List[Dict],
            "images": List[Dict],
            "scenarios": Dict[str, Dict[str, Any]],
            "root_path": str,
        }
    """
    base_dir = data_dir or _get_project_data_dir()
    videos: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []

    sync_metadata = load_cityflow_sync_metadata(base_dir)

    if not base_dir.exists():
        return {
            "videos": [],
            "images": [],
            "scenarios": {},
            "root_path": str(base_dir),
        }

    for root, _, files in os.walk(base_dir):
        root_path = Path(root)
        for f in files:
            file_path = root_path / f
            ext = file_path.suffix.lower()

            try:
                rel_path = file_path.relative_to(base_dir).as_posix()
            except ValueError:
                rel_path = str(file_path)

            parts = [p.lower() for p in file_path.relative_to(base_dir).parts]

            # Detect Camera ID candidate (e.g. c020, c001, c035)
            cam_id = None
            for p in parts:
                if (p.startswith("c0") or p.startswith("c1") or p.startswith("c2")) and len(p) <= 5:
                    cam_id = p
                    break

            # Detect Scenario: Check folder path or lookup in sync_metadata
            scenario = "General"
            for sc, sc_cams in sync_metadata.items():
                if sc.lower() in [p.lower() for p in parts]:
                    scenario = sc
                    break
                elif cam_id and cam_id in sc_cams:
                    scenario = sc
                    break

            # 1. Video files
            if ext in VIDEO_EXTENSIONS:
                width, height, fps, frame_count, duration_s = 0, 0, 10.0, 0, 0.0
                try:
                    cap = cv2.VideoCapture(str(file_path))
                    if cap.isOpened():
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps_val = cap.get(cv2.CAP_PROP_FPS)
                        if fps_val and fps_val > 0.1:
                            fps = round(float(fps_val), 2)
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        if frame_count > 0 and fps > 0:
                            duration_s = round(frame_count / fps, 2)
                        cap.release()
                except Exception:
                    pass

                # Check sync metadata
                sync_info = sync_metadata.get(scenario, {}).get(cam_id or "") if cam_id else None
                start_offset_s = sync_info.get("start_timestamp_s") if sync_info else None

                videos.append({
                    "id": rel_path,
                    "path": rel_path,
                    "filename": f,
                    "relative_path": rel_path,
                    "absolute_path": str(file_path),
                    "scenario": scenario,
                    "camera_id": cam_id,
                    "resolution": f"{width}x{height}" if width and height else "Unknown",
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "frame_count": frame_count,
                    "duration_s": duration_s,
                    "sync_offset_s": start_offset_s,
                    "size_bytes": file_path.stat().st_size,
                })

            # 2. Image files
            elif ext in IMAGE_EXTENSIONS:
                width, height = 0, 0
                try:
                    img = cv2.imread(str(file_path))
                    if img is not None:
                        height, width = img.shape[:2]
                except Exception:
                    pass

                images.append({
                    "id": rel_path,
                    "path": rel_path,
                    "filename": f,
                    "relative_path": rel_path,
                    "absolute_path": str(file_path),
                    "scenario": scenario,
                    "camera_id": cam_id,
                    "resolution": f"{width}x{height}" if width and height else "Unknown",
                    "width": width,
                    "height": height,
                    "format": ext.replace(".", "").upper(),
                    "size_bytes": file_path.stat().st_size,
                })

    videos.sort(key=lambda v: (v["scenario"], v.get("camera_id") or "", v["filename"]))
    images.sort(key=lambda i: (i["scenario"], i["filename"]))

    return {
        "videos": videos,
        "images": images,
        "scenarios": sync_metadata,
        "root_path": str(base_dir),
    }
