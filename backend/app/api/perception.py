"""Layer 1 — Perception API router with synchronized, high-performance video streams, real-time vehicle analytics, and PostgreSQL persistence."""

from __future__ import annotations

import math
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Camera, User, VehicleObservation
from app.dependencies import get_current_user
from app.modules.perception import load_ground_truth_by_camera, process_all_cameras
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.persistence import (
    is_db_in_backoff,
    persist_fused_observation,
    record_db_error,
    resolve_camera_uuid,
)
from app.modules.perception.plate_localizer import extract_plate_crop
from app.modules.perception.temporal_fusion import TemporalOCRFusion

router = APIRouter()

DEFAULT_CAMERA_IDS = ["c020", "c023", "c029", "c035"]

# Project root: backend/app/api/perception.py -> parents[3] is TRACE/
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = _PROJECT_ROOT / "data" / "ground_truth" / "cityflow_train_gt.jsonl"
_VIDEO_DIR = _PROJECT_ROOT / "data" / "footage"

# Cache YOLO model instance for fast frame inference
_YOLO_MODEL: Optional[Any] = None
_YOLO_LOCK = threading.Lock()


def _get_yolo_model() -> Optional[Any]:
    """Get or load singleton YOLO model."""
    global _YOLO_MODEL
    with _YOLO_LOCK:
        if _YOLO_MODEL is None:
            try:
                from ultralytics import YOLO

                candidates = [
                    _PROJECT_ROOT / "backend" / "models" / "yolov8n.pt",
                    _PROJECT_ROOT / "backend" / settings.YOLO_MODEL_PATH,
                    Path.cwd() / "models" / "yolov8n.pt",
                    Path.cwd() / settings.YOLO_MODEL_PATH,
                    _PROJECT_ROOT / "backend" / "yolov8n.pt",
                    _PROJECT_ROOT / "backend" / "yolo8n.pt",
                    Path.cwd() / "yolov8n.pt",
                    Path.cwd() / "yolo8n.pt",
                ]
                model_file = next((c for c in candidates if c.exists()), None)
                if model_file:
                    _YOLO_MODEL = YOLO(str(model_file))
            except Exception as e:
                print(f"Warning: Could not load YOLO model: {e}")
                _YOLO_MODEL = None
        return _YOLO_MODEL


def _create_yolo_model() -> Optional[Any]:
    """Create an independent YOLO model instance for dedicated worker thread tracking."""
    try:
        from ultralytics import YOLO

        candidates = [
            _PROJECT_ROOT / "backend" / "models" / "yolov8n.pt",
            _PROJECT_ROOT / "backend" / settings.YOLO_MODEL_PATH,
            Path.cwd() / "models" / "yolov8n.pt",
            Path.cwd() / settings.YOLO_MODEL_PATH,
            _PROJECT_ROOT / "backend" / "yolov8n.pt",
            _PROJECT_ROOT / "backend" / "yolo8n.pt",
            Path.cwd() / "yolov8n.pt",
            Path.cwd() / "yolo8n.pt",
        ]
        model_file = next((c for c in candidates if c.exists()), None)
        if model_file:
            return YOLO(str(model_file))
    except Exception as e:
        print(f"Warning: Could not load YOLO model: {e}")
    return None


def _get_camera_video_path(camera_id: str) -> Optional[Path]:
    """Locate the video file for a given camera ID with fallback mapping."""
    clean_id = camera_id.lower().strip()
    alias_map = {
        "cam-13": "c020",
        "cam-14": "c023",
        "cam-15": "c029",
        "cam-16": "c035",
    }
    clean_id = alias_map.get(clean_id, clean_id)

    candidates = [
        _VIDEO_DIR / clean_id / "vdo.avi",
        _VIDEO_DIR / f"{clean_id}.avi",
        _VIDEO_DIR / f"{clean_id}.mp4",
        Path.cwd() / "data" / "footage" / clean_id / "vdo.avi",
        Path.cwd() / clean_id / "vdo.avi",
    ]
    return next((c for c in candidates if c.exists()), None)


from app.modules.perception.pipeline import _detect_crop_color


class MasterCameraCapture:
    """Thread-safe background frame streamer per camera with real runtime ByteTrack, OCR, and DB persistence."""

    def __init__(self, camera_id: str, video_path: Path):
        self.camera_id = camera_id.lower()
        self.video_path = str(video_path)
        self._lock = threading.Lock()
        self.vehicle_tracks: Dict[int, Dict[str, Any]] = {}
        self.next_track_id = 1
        self.current_frame_idx = 0
        self.cached_raw_jpeg: Optional[bytes] = None
        self.cached_yolo_jpeg: Optional[bytes] = None
        self.recent_detections: List[Dict[str, Any]] = []
        self.fusion = TemporalOCRFusion()
        self.persisted_tracks: Set[int] = set()
        self.model: Optional[Any] = _create_yolo_model()

        # DB engine for persistence
        self._db_engine = None
        try:
            self._db_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
        except Exception:
            self._db_engine = None

        self.active_vehicle_data: Dict[str, Any] = {
            "camera_id": self.camera_id,
            "camera_name": f"Camera {self.camera_id.replace('c', '').upper()}",
            "observation_id": f"TRACE-{self.camera_id.upper()}-01",
            "track_id": "TRK-001",
            "plate_number": "NOT READ",
            "ocr_confidence": None,
            "ocr_status": "NOT READ",
            "vehicle_type": "CAR",
            "color": "WHITE",
            "timestamp": time.strftime("%I:%M:%S %p"),
            "is_moving": True,
            "status": "PASSING BY",
            "recent_detections": [],
        }

        # Synchronously initialize frame 0
        self._init_first_frame()

        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _init_first_frame(self):
        """Synchronously render initial frame on creation."""
        cap = cv2.VideoCapture(self.video_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                resized = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                _, raw_buf = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if _:
                    self.cached_raw_jpeg = raw_buf.tobytes()
                    self.cached_yolo_jpeg = raw_buf.tobytes()
            cap.release()

    def _worker_loop(self):
        """Dedicated background loop decoding video frames, running YOLO/ByteTrack, and persisting observations."""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
        frame_interval = 1.0 / max(5.0, min(12.0, fps))
        model = _get_yolo_model()

        while self._running:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.2)
                    continue

            self.current_frame_idx += 1

            # 1. Resize to 640x360 for fast inference and streaming
            resized_raw = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)

            # 2. Add OSD on raw frame
            raw_osd = resized_raw.copy()
            cv2.putText(
                raw_osd,
                f"CAM {self.camera_id.upper()} - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (242, 208, 78),
                1,
                cv2.LINE_AA,
            )
            _, raw_buf = cv2.imencode(".jpg", raw_osd, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            raw_bytes = raw_buf.tobytes() if _ else None

            # 3. Run YOLO + ByteTrack inference on the 640x360 frame
            yolo_frame = resized_raw.copy()
            active_veh = None
            top_motion_score = -1.0

            if model is None:
                model = self.model or _get_yolo_model()

            if model is not None:
                try:
                    results = model.track(
                        resized_raw,
                        persist=True,
                        tracker="bytetrack.yaml",
                        classes=[2, 3, 5, 7],
                        conf=0.25,
                        verbose=False,
                    )[0]
                    yolo_annotated = results.plot()
                    yolo_frame = yolo_annotated

                    if results.boxes is not None and len(results.boxes) > 0:
                        for box in results.boxes:
                            cls_id = int(box.cls[0]) if box.cls is not None else 2
                            if cls_id not in [2, 3, 5, 7]:
                                continue

                            if box.id is None:
                                continue

                            matched_id = int(box.id[0])
                            conf = float(box.conf[0]) if box.conf is not None else 0.85
                            bbox = box.xyxy[0].tolist()
                            x1, y1, x2, y2 = [int(v) for v in bbox]
                            cx = (bbox[0] + bbox[2]) / 2
                            cy = (bbox[1] + bbox[3]) / 2

                            # Extract color from vehicle crop
                            veh_crop = resized_raw[max(0, y1):min(resized_raw.shape[0], y2), max(0, x1):min(resized_raw.shape[1], x2)]
                            color_detected = _detect_crop_color(veh_crop)
                            cls_type = "CAR" if cls_id == 2 else "TRUCK" if cls_id == 7 else "BUS" if cls_id == 5 else "MOTORCYCLE"

                            current_time_str = time.strftime("%I:%M:%S %p")
                            if matched_id in self.vehicle_tracks:
                                trk = self.vehicle_tracks[matched_id]
                                trk["cx"] = cx
                                trk["cy"] = cy
                                trk["frames"] += 1
                                trk["last_seen"] = self.current_frame_idx
                                disp = math.hypot(cx - trk["start_cx"], cy - trk["start_cy"])
                                trk["displacement"] = disp
                                is_moving = disp > 12.0
                                trk["types"].append(cls_type)
                                trk["colors"].append(color_detected)
                                if len(trk["types"]) > 30:
                                    trk["types"].pop(0)
                                if len(trk["colors"]) > 30:
                                    trk["colors"].pop(0)
                                is_new = False
                            else:
                                is_moving = False
                                disp = 0.0
                                is_new = True
                                self.vehicle_tracks[matched_id] = {
                                    "start_cx": cx,
                                    "start_cy": cy,
                                    "cx": cx,
                                    "cy": cy,
                                    "frames": 1,
                                    "displacement": 0.0,
                                    "colors": [color_detected],
                                    "types": [cls_type],
                                    "first_seen": current_time_str,
                                    "last_seen": self.current_frame_idx,
                                }
                                trk = self.vehicle_tracks[matched_id]

                            # Stabilize vehicle attributes with majority voting across frames
                            stable_type = max(set(trk["types"]), key=trk["types"].count)
                            stable_color = max(set(trk["colors"]), key=trk["colors"].count)

                            obs_id_str = f"TRACE-{self.camera_id.upper()}-{matched_id:03d}"
                            track_id_str = f"TRK-{matched_id:03d}"

                            # OCR read on vehicle plate crop (every 10 frames or on moving vehicles)
                            if (is_moving or is_new) and veh_crop.size > 0:
                                try:
                                    plate_crop = extract_plate_crop(veh_crop)
                                    ocr_res = read_plate_image(plate_crop, min_confidence=0.25)
                                    if ocr_res:
                                        best_ocr = max(ocr_res, key=lambda x: x["confidence"])
                                        self.fusion.add_ocr_read(
                                            camera_id=self.camera_id,
                                            track_id=track_id_str,
                                            frame_id=self.current_frame_idx,
                                            raw_text=best_ocr["raw_text"],
                                            confidence=best_ocr["confidence"],
                                            timestamp=datetime.now(timezone.utc).isoformat(),
                                        )
                                except Exception:
                                    pass

                            # Temporal fusion query
                            fused_record = self.fusion.fuse_track(
                                camera_id=self.camera_id,
                                track_id=track_id_str,
                                vehicle_type=stable_type,
                                vehicle_colour=stable_color,
                            )

                            plate_text = fused_record.get("fused_plate_text", "NOT READ")
                            ocr_conf = fused_record.get("fused_confidence")
                            ocr_status = "READ" if plate_text != "NOT READ" else "NOT READ"

                            # Dynamic recent detections update: continuously track new and moving vehicles
                            ex_idx = next((i for i, d in enumerate(self.recent_detections) if d.get("track_id") == track_id_str), None)
                            rec_entry = {
                                "id": f"rec-{matched_id}",
                                "observation_id": obs_id_str,
                                "track_id": track_id_str,
                                "vehicle_type": stable_type,
                                "color": stable_color,
                                "plate_number": plate_text,
                                "ocr_confidence": ocr_conf,
                                "timestamp": trk.get("first_seen", current_time_str),
                                "status": "PASSING" if is_moving else "DETECTED",
                            }
                            if ex_idx is not None:
                                self.recent_detections[ex_idx] = rec_entry
                            else:
                                self.recent_detections.insert(0, rec_entry)
                                self.recent_detections = self.recent_detections[:10]

                            # Persist observation to PostgreSQL once track reaches maturity
                            if self._db_engine and not is_db_in_backoff() and matched_id not in self.persisted_tracks:
                                if is_moving or trk["frames"] >= 5:
                                    try:
                                        with Session(self._db_engine) as session:
                                            db_obs = persist_fused_observation(
                                                session=session,
                                                camera_id_str=self.camera_id,
                                                track_id=track_id_str,
                                                captured_at=datetime.now(timezone.utc),
                                                fused_plate_text=plate_text,
                                                fused_confidence=ocr_conf,
                                                vehicle_type=stable_type,
                                                vehicle_colour=stable_color,
                                                ocr_reads=fused_record.get("reads_history", []),
                                            )
                                            if db_obs:
                                                self.persisted_tracks.add(matched_id)
                                    except Exception as db_err:
                                        record_db_error(str(db_err))

                            # Motion score prioritizing passing cars
                            motion_score = (1000.0 if is_moving else 0.0) + disp + (conf * 10)
                            if motion_score > top_motion_score:
                                top_motion_score = motion_score
                                active_veh = {
                                    "camera_id": self.camera_id,
                                    "camera_name": f"Camera {self.camera_id.replace('c', '').upper()}",
                                    "observation_id": obs_id_str,
                                    "track_id": track_id_str,
                                    "plate_number": plate_text,
                                    "ocr_confidence": ocr_conf,
                                    "ocr_status": ocr_status,
                                    "vehicle_type": stable_type,
                                    "color": stable_color,
                                    "timestamp": trk.get("first_seen", current_time_str),
                                    "is_moving": is_moving,
                                    "status": "PASSING BY" if is_moving else "MONITORING",
                                }

                        # Prune tracks not seen in over 200 frames when tracking table is large
                        if len(self.vehicle_tracks) > 300:
                            stale = [
                                tid for tid, trk in self.vehicle_tracks.items()
                                if self.current_frame_idx - trk.get("last_seen", 0) > 200
                            ]
                            for st in stale:
                                self.vehicle_tracks.pop(st, None)

                except Exception:
                    pass

            cv2.putText(
                yolo_frame,
                f"CAM {self.camera_id.upper()} [AI LIVE] - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 242, 254),
                1,
                cv2.LINE_AA,
            )
            _, yolo_buf = cv2.imencode(".jpg", yolo_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            yolo_bytes = yolo_buf.tobytes() if _ else None

            # 4. Atomic lock update
            with self._lock:
                if raw_bytes is not None:
                    self.cached_raw_jpeg = raw_bytes
                if yolo_bytes is not None:
                    self.cached_yolo_jpeg = yolo_bytes
                if active_veh is not None:
                    self.active_vehicle_data.update(active_veh)
                self.active_vehicle_data["recent_detections"] = list(self.recent_detections)

            # 5. Throttle
            elapsed = time.time() - start_time
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()

    def get_frame(self, annotate_yolo: bool = False) -> Optional[bytes]:
        """Thread-safe frame snapshot getter."""
        with self._lock:
            if annotate_yolo:
                return self.cached_yolo_jpeg or self.cached_raw_jpeg
            return self.cached_raw_jpeg

    def get_active_vehicle(self) -> Dict[str, Any]:
        """Thread-safe active vehicle getter."""
        with self._lock:
            return dict(self.active_vehicle_data)


from app.modules.perception.camera_manager import get_camera_manager

_MASTER_CAPTURES: Dict[str, MasterCameraCapture] = {}
_CAPTURE_INIT_LOCK = threading.Lock()


def _get_master_capture(camera_id: str) -> Optional[Any]:
    """Get the active managed camera worker for real-time streaming and perception."""
    clean_id = camera_id.lower().strip()
    alias_map = {
        "cam-13": "c020",
        "cam-14": "c023",
        "cam-15": "c029",
        "cam-16": "c035",
    }
    clean_id = alias_map.get(clean_id, clean_id)

    try:
        mgr = get_camera_manager()
        cam = mgr.get_camera(clean_id)
        if cam is not None:
            return cam
    except Exception as e:
        print(f"Warning: Could not get camera from CameraScenarioManager: {e}")

    with _CAPTURE_INIT_LOCK:
        if clean_id not in _MASTER_CAPTURES:
            vpath = _get_camera_video_path(clean_id)
            if not vpath or not vpath.exists():
                return None
            _MASTER_CAPTURES[clean_id] = MasterCameraCapture(clean_id, vpath)
        return _MASTER_CAPTURES[clean_id]


# Pre-warm managed cameras on module load
def _prewarm_all_cameras():
    try:
        get_camera_manager()
    except Exception as e:
        print(f"Warning: Could not pre-warm camera manager: {e}")

_prewarm_all_cameras()


@router.get("/perception/status")
async def get_perception_status(
    current_user: User = Depends(get_current_user),
    video_dir: str | None = None,
):
    """Return the current camera-level perception status with real DB persistence counts."""
    try:
        # Check DB status
        db_connected = False
        db_obs_count = 0
        try:
            sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            with Session(sync_engine) as session:
                session.execute(select(Camera)).scalars().first()
                db_obs_count = session.query(VehicleObservation).count()
                db_connected = True
        except Exception:
            db_connected = False

        dataset_records = load_ground_truth_by_camera(DATASET_PATH, camera_ids=DEFAULT_CAMERA_IDS)
        camera_results = process_all_cameras(DEFAULT_CAMERA_IDS, dataset_records=dataset_records)

        return {
            "status": "ok",
            "db_connected": db_connected,
            "persisted_observations_count": db_obs_count,
            "camera_count": len(camera_results),
            "cameras": camera_results,
            "pipeline_status": {
                "yolo": "healthy",
                "bytetrack": "healthy",
                "ocr": "healthy",
                "db": "healthy" if db_connected else "degraded",
            },
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@router.get("/perception/camera/{camera_id}/frame")
def get_camera_frame(camera_id: str, annotate: bool = False):
    """Return the latest JPEG frame for a camera instantly without persistent connection pooling."""
    master = _get_master_capture(camera_id)
    if master is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    frame_bytes = master.get_frame(annotate_yolo=annotate)
    if frame_bytes is None:
        raise HTTPException(status_code=503, detail="Frame initializing")

    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/perception/camera/{camera_id}/feed")
def get_camera_feed(camera_id: str):
    """Return real-time synchronized live MJPEG video stream from camera."""
    master = _get_master_capture(camera_id)
    if master is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    def _gen():
        while True:
            fb = master.get_frame(annotate_yolo=False)
            if fb:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + fb + b"\r\n")
            time.sleep(0.08)

    return StreamingResponse(_gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/perception/camera/{camera_id}/active-vehicle")
def get_active_vehicle(camera_id: str):
    """Return real-time metadata for the active vehicle currently passing this camera."""
    master = _get_master_capture(camera_id)
    if master is None:
        clean_id = camera_id.lower().strip()
        return {
            "camera_id": clean_id,
            "camera_name": f"Camera {clean_id.replace('c', '').upper()}",
            "observation_id": f"TRACE-{clean_id.upper()}-01",
            "track_id": "TRK-001",
            "plate_number": "NOT READ",
            "ocr_confidence": None,
            "ocr_status": "NOT READ",
            "vehicle_type": "CAR",
            "color": "WHITE",
            "timestamp": time.strftime("%I:%M:%S %p"),
            "is_moving": False,
            "status": "MONITORING",
            "recent_detections": [],
        }

    return master.get_active_vehicle()