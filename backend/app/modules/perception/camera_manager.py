"""Layer 1 — Perception Module: Unified Runtime Camera Input, Playback, and Scenario Synchronization Manager."""

from __future__ import annotations

import base64
import json
import logging
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from app.config import settings
from app.modules.appearance.preprocessing import score_crop_quality
from app.modules.perception.normalization import normalize_plate_text
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.persistence import (
    is_db_in_backoff,
    persist_fused_observation,
    record_db_error,
    upsert_observation_embedding,
)
from app.modules.perception.pipeline import _detect_crop_color
from app.modules.perception.plate_localizer import extract_plate_crop
from app.modules.perception.source_discovery import (
    _get_project_data_dir,
    discover_sources,
    load_cityflow_sync_metadata,
)
from app.modules.perception.temporal_fusion import TemporalOCRFusion

logger = logging.getLogger("trace.perception.camera_manager")

CONFIG_FILE_NAME = "camera_config.json"
_PROJECT_ROOT = Path(__file__).resolve().parents[4]

_CAMERA_GEO_METADATA: Dict[str, Dict[str, Any]] = {
    "c020": {
        "name": "Camera 020 (W Locust & Grandview)",
        "location": "W Locust & Grandview",
        "latitude": 42.5039,
        "longitude": -90.6865,
        "resolution": "1080P",
    },
    "c023": {
        "name": "Camera 023 (Grandview & Delhi)",
        "location": "Grandview & Delhi",
        "latitude": 42.5055,
        "longitude": -90.6784,
        "resolution": "1080P",
    },
    "c029": {
        "name": "Camera 029 (N Grandview & University)",
        "location": "N Grandview & University",
        "latitude": 42.5085,
        "longitude": -90.6710,
        "resolution": "1080P",
    },
    "c035": {
        "name": "Camera 035 (Highway 20 Corridor)",
        "location": "Highway 20 Corridor",
        "latitude": 42.5115,
        "longitude": -90.6635,
        "resolution": "1080P",
    },
}
 
 
def letterbox_image(
    image: np.ndarray,
    target_w: int = 640,
    target_h: int = 360,
    pad_color: Tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    """Scale and fit an image into (target_w, target_h) preserving aspect ratio with letterbox/pillarbox padding."""
    if image is None or image.size == 0:
        return np.zeros((target_h, target_w, 3), dtype=np.uint8)

    h, w = image.shape[:2]
    if w == target_w and h == target_h:
        return image.copy()

    # If aspect ratio is already within 2% of target 16:9, scale directly
    aspect_diff = abs((w / h) - (target_w / target_h))
    if aspect_diff < 0.02:
        interp = cv2.INTER_AREA if w > target_w else cv2.INTER_LINEAR
        return cv2.resize(image, (target_w, target_h), interpolation=interp)

    scale = min(target_w / w, target_h / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    resized = cv2.resize(image, (new_w, new_h), interpolation=interp)

    canvas = np.full((target_h, target_w, 3), pad_color, dtype=np.uint8)
    pad_x = max(0, (target_w - new_w) // 2)
    pad_y = max(0, (target_h - new_h) // 2)

    canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
    return canvas


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
                logger.warning(f"Could not load YOLO model: {e}")
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
        logger.warning(f"Could not load YOLO model: {e}")
    return None


def _get_config_path() -> Path:
    """Path to the persistent camera configuration JSON file."""
    return _get_project_data_dir() / CONFIG_FILE_NAME


class CameraPlaybackController:
    """Master scenario timeline and synchronization clock."""

    def __init__(self):
        self._lock = threading.Lock()
        self.sync_mode: str = "synchronized"  # "synchronized" | "independent"
        self.playback_state: str = "playing"  # "playing" | "paused" | "stopped"
        self.playback_speed: float = 1.0     # 0.25, 0.5, 1.0, 2.0, 4.0
        self.master_time_s: float = 0.0
        self.loop_scenario: bool = True
        self.last_tick_time: float = time.time()
        self.max_scenario_duration_s: float = 190.0
        self.seek_version: int = 0

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sync_mode": self.sync_mode,
                "playback_state": self.playback_state,
                "playback_speed": self.playback_speed,
                "master_time_s": round(self.master_time_s, 3),
                "master_time_formatted": self.format_time(self.master_time_s),
                "max_duration_s": self.max_scenario_duration_s,
                "max_duration_formatted": self.format_time(self.max_scenario_duration_s),
                "loop_scenario": self.loop_scenario,
            }

    @staticmethod
    def format_time(seconds: float) -> str:
        s = max(0.0, seconds)
        mins = int(s // 60)
        secs = int(s % 60)
        millis = int((s - int(s)) * 1000)
        return f"{mins:02d}:{secs:02d}.{millis:03d}"

    def update_settings(
        self,
        sync_mode: Optional[str] = None,
        playback_state: Optional[str] = None,
        playback_speed: Optional[float] = None,
        loop_scenario: Optional[bool] = None,
        seek_time_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if sync_mode in ["synchronized", "independent"]:
                if self.sync_mode != sync_mode:
                    self.sync_mode = sync_mode
                    self.seek_version += 1
            if playback_state in ["playing", "paused", "stopped"]:
                self.playback_state = playback_state
                self.last_tick_time = time.time()
            if playback_speed and playback_speed > 0:
                self.playback_speed = float(playback_speed)
            if loop_scenario is not None:
                self.loop_scenario = bool(loop_scenario)
            if seek_time_s is not None:
                self.master_time_s = max(0.0, float(seek_time_s))
                self.last_tick_time = time.time()
                self.seek_version += 1
        return self.get_status()

    def tick(self) -> float:
        with self._lock:
            now = time.time()
            dt = now - self.last_tick_time
            self.last_tick_time = now

            if self.playback_state == "playing":
                self.master_time_s += dt * self.playback_speed
                if self.master_time_s > self.max_scenario_duration_s:
                    if self.loop_scenario:
                        self.master_time_s = 0.0
                        self.seek_version += 1
                    else:
                        self.playback_state = "stopped"
            return self.master_time_s


class ManagedCameraWorker:
    """Individual runtime worker streaming a single camera (Video or Image) with CityFlow sync."""

    def __init__(self, camera_id: str, config: Dict[str, Any], controller: CameraPlaybackController):
        self.camera_id = camera_id.lower()
        self.controller = controller
        self._lock = threading.Lock()
        self._running = False
        self._generation: int = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None

        # Configuration properties
        geo = _CAMERA_GEO_METADATA.get(self.camera_id, {})
        self.name: str = config.get("name") or geo.get("name") or f"Camera {self.camera_id.upper()}"
        self.location: str = config.get("location") or geo.get("location") or "CityFlow S04 Corridor"
        self.latitude: float = float(config.get("latitude") or geo.get("latitude") or 42.507)
        self.longitude: float = float(config.get("longitude") or geo.get("longitude") or -90.675)
        self.resolution: str = config.get("resolution") or geo.get("resolution") or "1080P"
        self.source_type: str = config.get("source_type", "video").lower()
        self.source_path: str = config.get("source_path", "")
        self.scenario: str = config.get("scenario", "S04")
        self.fps: float = float(config.get("fps", 10.0))
        self.enabled: bool = bool(config.get("enabled", True))
        self.sync_offset_s: float = float(config.get("sync_offset_s") or 0.0)
        self.frame_count: Optional[int] = config.get("frame_count")
        self.total_frames: int = int(config.get("frame_count") or 0)

        # Runtime State
        self.status_label: str = "INITIALIZING"
        self.current_frame_idx: int = 0
        self.current_local_time_s: float = 0.0
        self.cached_raw_jpeg: Optional[bytes] = None
        self.cached_yolo_jpeg: Optional[bytes] = None
        self.vehicle_tracks: Dict[int, Dict[str, Any]] = {}
        self.next_track_id: int = 1
        self.recent_detections: List[Dict[str, Any]] = []
        self.persisted_tracks: set[int] = set()
        self.fusion = TemporalOCRFusion()
        self.last_seek_version: int = 0
        self.model: Optional[Any] = _create_yolo_model()
        self.current_detection_count: int = 0

        # Active Observation
        self.active_vehicle_data: Dict[str, Any] = {
            "camera_id": self.camera_id,
            "camera_name": self.name,
            "observation_id": f"TRACE-{self.camera_id.upper()}-01",
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

        # Condition variable for non-polling, zero-duplicate frame streaming
        self._frame_cond = threading.Condition(self._lock)

        # Dedicated background executor for non-blocking perception tasks (PaddleOCR, ResNet, DB persistence)
        self._bg_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"cam-{self.camera_id}-bg")

        # DB Engine for persistence
        from sqlalchemy import create_engine
        try:
            self._db_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
        except Exception:
            self._db_engine = None

        # Start worker
        self.start()

    def start(self):
        with self._lock:
            if self._running and self._thread and self._thread.is_alive():
                return
            self._running = True
            self._generation += 1
            current_gen = self._generation
            self._stop_event = threading.Event()
            stop_evt = self._stop_event
            self._thread = threading.Thread(
                target=self._worker_loop,
                args=(current_gen, stop_evt),
                name=f"CameraWorker-{self.camera_id}-g{current_gen}",
                daemon=True,
            )
            self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False
            self._generation += 1
            if hasattr(self, "_stop_event"):
                self._stop_event.set()
            if hasattr(self, "_frame_cond"):
                self._frame_cond.notify_all()
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
            thread_to_join = self._thread
            self._thread = None

        if hasattr(self, "_bg_executor"):
            try:
                self._bg_executor.shutdown(wait=False)
            except Exception:
                pass

        if thread_to_join and thread_to_join.is_alive():
            thread_to_join.join(timeout=2.0)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            sync_active = (self.controller.sync_mode == "synchronized")
            is_active = self.enabled and self.status_label not in ["DISABLED", "FAILED", "OFFLINE"]
            status = "ONLINE" if is_active else ("DISABLED" if not self.enabled else self.status_label)
            return {
                "camera_id": self.camera_id,
                "name": self.name,
                "location": self.location,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "resolution": self.resolution,
                "source_type": self.source_type,
                "source_path": self.source_path,
                "scenario": self.scenario,
                "fps": self.fps,
                "enabled": self.enabled,
                "sync_offset_s": self.sync_offset_s,
                "frame_count": self.frame_count,
                "total_frames": self.total_frames,
                "status": status,
                "raw_status": self.status_label,
                "sync_mode": self.controller.sync_mode,
                "current_frame": self.current_frame_idx,
                "current_local_time": round(self.current_local_time_s, 2),
            }

    def _resolve_full_path(self) -> Path:
        data_dir = _get_project_data_dir()
        p = Path(self.source_path)
        if p.is_absolute() and p.exists():
            return p
        candidate1 = data_dir / self.source_path
        if candidate1.exists():
            return candidate1
        candidate2 = data_dir / "footage" / self.source_path
        if candidate2.exists():
            return candidate2
        return candidate1

    def _reset_tracking_state(self):
        """Reset tracking state, vehicle history, and ByteTrack tracker on timeline reset/seek."""
        with self._lock:
            self.vehicle_tracks.clear()
            self.persisted_tracks.clear()
            self.fusion = TemporalOCRFusion()
            self.recent_detections.clear()
        if self.model is not None:
            try:
                if hasattr(self.model, "predictor") and self.model.predictor:
                    trackers = getattr(self.model.predictor, "trackers", [])
                    for t in trackers:
                        t.reset()
            except Exception:
                pass

    def _worker_loop(self, generation: int, stop_event: threading.Event):
        """Dedicated execution loop for video or image source."""
        resolved_path = self._resolve_full_path()

        # Handle Still Image source
        if self.source_type == "image":
            self._run_image_loop(resolved_path, generation, stop_event)
            return

        # Handle Video source
        if not resolved_path.exists():
            with self._lock:
                if self._generation == generation:
                    self.status_label = "OFFLINE"
            return

        cap = cv2.VideoCapture(str(resolved_path))
        with self._lock:
            if stop_event.is_set() or self._generation != generation or not self._running:
                cap.release()
                return
            self._cap = cap

        if not cap.isOpened():
            with self._lock:
                if self._generation == generation:
                    self.status_label = "FAILED"
                if self._cap is cap:
                    self._cap = None
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or (self.frame_count or 9999)
        self.frame_count = total_frames
        self.total_frames = total_frames
        video_fps = cap.get(cv2.CAP_PROP_FPS) or self.fps or 10.0

        last_rendered_frame_idx = -1
        next_frame_time = time.monotonic()

        try:
            while not stop_event.is_set() and self._running and self._generation == generation:

                if not self.enabled:
                    with self._lock:
                        self.status_label = "DISABLED"
                    stop_event.wait(0.2)
                    continue

                master_time = self.controller.master_time_s
                sync_mode = self.controller.sync_mode
                play_state = self.controller.playback_state

                # 1. Handle Reset 00:00 or Timeline Seek in BOTH Independent and Sync modes
                if self.last_seek_version != self.controller.seek_version:
                    self.last_seek_version = self.controller.seek_version
                    self._reset_tracking_state()
                    if sync_mode == "synchronized":
                        local_time = master_time - self.sync_offset_s
                        self.current_local_time_s = max(0.0, local_time)
                        if local_time < 0.0:
                            with self._lock:
                                self.status_label = "WAITING"
                            self._render_waiting_frame(countdown=-local_time)
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            last_rendered_frame_idx = -1
                            self.current_frame_idx = 0
                            stop_event.wait(0.05)
                            continue
                        else:
                            target_f = min(total_frames - 1, max(0, int(local_time * self.fps)))
                            cap.set(cv2.CAP_PROP_POS_FRAMES, target_f)
                            last_rendered_frame_idx = target_f - 1
                            self.current_frame_idx = target_f
                    else:
                        # Independent Mode: clicking Reset immediately rewinds video to frame 0
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        last_rendered_frame_idx = -1
                        self.current_frame_idx = 0
                        self.current_local_time_s = 0.0

                if play_state == "paused":
                    stop_event.wait(0.08)
                    continue

                if play_state == "stopped":
                    stop_event.wait(0.08)
                    continue

                if sync_mode == "synchronized":
                    # CityFlow synchronization formula: T_local = T_master - T_start
                    local_time = master_time - self.sync_offset_s
                    self.current_local_time_s = max(0.0, local_time)

                    if local_time < 0.0:
                        # Camera waiting for its scenario entry time
                        with self._lock:
                            self.status_label = "WAITING"
                        self._render_waiting_frame(countdown=-local_time)
                        if last_rendered_frame_idx != -1:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            last_rendered_frame_idx = -1
                            self.current_frame_idx = 0
                        stop_event.wait(0.05)
                        continue

                    if last_rendered_frame_idx >= total_frames - 1:
                        # Reached end of scenario footage -> hold cleanly on last frame
                        with self._lock:
                            self.status_label = "SOURCE ENDED"
                        stop_event.wait(0.1)
                        continue

                    with self._lock:
                        self.status_label = "PROCESSING"
                else:
                    # Independent Testing Mode: loop independently at native FPS
                    with self._lock:
                        self.status_label = "SYNC DISABLED"

                # Sequential frame read
                ret, frame = cap.read()
                if not ret:
                    if sync_mode == "independent":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        last_rendered_frame_idx = -1
                        self._reset_tracking_state()
                        ret, frame = cap.read()
                    else:
                        with self._lock:
                            self.status_label = "SOURCE ENDED"
                        stop_event.wait(0.1)
                        continue

                if not ret or frame is None:
                    stop_event.wait(0.05)
                    continue

                if stop_event.is_set() or self._generation != generation or not self._running:
                    break

                last_rendered_frame_idx += 1
                self.current_frame_idx = last_rendered_frame_idx
                if sync_mode != "synchronized":
                    self.current_local_time_s = round(self.current_frame_idx / self.fps, 2)

                # Process frame through perception pipeline
                self._process_and_cache_frame(frame, self.current_frame_idx, generation, stop_event)

                # Precise monotonic deadline pacing to eliminate micro-stutters and frame drift
                target_fps = max(1.0, self.fps * self.controller.playback_speed)
                target_interval = 1.0 / target_fps
                next_frame_time += target_interval
                now = time.monotonic()
                sleep_time = next_frame_time - now

                if sleep_time > 0:
                    stop_event.wait(sleep_time)
                else:
                    # If inference or disk access fell slightly behind, resync deadline to prevent rapid burst catch-up
                    next_frame_time = now
        finally:
            cap.release()
            with self._lock:
                if self._cap is cap:
                    self._cap = None

    def _render_waiting_frame(self, countdown: float):
        """Render a clean camera standby frame while waiting for CityFlow sync start."""
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(
            img,
            f"CAM {self.camera_id.upper()} — STANDBY",
            (160, 160),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (242, 208, 78),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img,
            f"Starts at Master T+{self.sync_offset_s:.1f}s (in {countdown:.1f}s)",
            (140, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (180, 180, 180),
            1,
            cv2.LINE_AA,
        )
        _, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if _:
            raw_bytes = buf.tobytes()
            with self._lock:
                self.cached_raw_jpeg = raw_bytes
                self.cached_yolo_jpeg = raw_bytes

    def _run_image_loop(self, image_path: Path, generation: int, stop_event: threading.Event):
        """Execution loop for Still Image camera sources."""
        if not image_path.exists():
            with self._lock:
                if self._generation == generation:
                    self.status_label = "IMAGE NOT FOUND"
            return

        img = cv2.imread(str(image_path))
        if img is None:
            with self._lock:
                if self._generation == generation:
                    self.status_label = "FAILED"
            return

        with self._lock:
            if self._generation == generation:
                self.status_label = "IMAGE ACTIVE"

        # Fit image with correct aspect ratio onto standard 640x360 canvas
        letterboxed = letterbox_image(img, 640, 360)

        # Process the image once for initial YOLO, OCR, and DB persistence
        self.current_frame_idx = 1
        self._process_and_cache_frame(letterboxed.copy(), 1, generation, stop_event)

        frame_idx = 1
        while not stop_event.is_set() and self._running and self._generation == generation:
            if not self.enabled:
                with self._lock:
                    self.status_label = "DISABLED"
                stop_event.wait(0.3)
                continue

            with self._lock:
                self.status_label = "IMAGE ACTIVE"

            frame_idx += 1
            self.current_frame_idx = frame_idx

            # Update OSD timestamp on letterboxed raw frame smoothly without warping
            raw_osd = letterboxed.copy()
            sync_label = "SYNC" if self.controller.sync_mode == "synchronized" else "INDEP"
            cv2.putText(
                raw_osd,
                f"CAM {self.camera_id.upper()} [{sync_label}] - F:{frame_idx} - {time.strftime('%H:%M:%S')}",
                (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (242, 208, 78),
                1,
                cv2.LINE_AA,
            )
            _, raw_buf = cv2.imencode(".jpg", raw_osd, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if _:
                with self._lock:
                    if self._generation == generation and self._running and not stop_event.is_set():
                        self.cached_raw_jpeg = raw_buf.tobytes()

            stop_event.wait(1.0 / max(1.0, self.fps))

    def _process_and_cache_frame(
        self,
        frame: np.ndarray,
        frame_id: int,
        generation: int = 0,
        stop_event: Optional[threading.Event] = None,
    ):
        """Run YOLOv8, ByteTrack, Plate Localization, PaddleOCR, and caching on the frame."""
        if (stop_event is not None and (stop_event.is_set() or self._generation != generation)) or not self._running:
            return

        resized_raw = letterbox_image(frame, 640, 360)

        # 1. Raw OSD frame
        raw_osd = resized_raw.copy()
        sync_label = "SYNC" if self.controller.sync_mode == "synchronized" else "INDEP"
        cv2.putText(
            raw_osd,
            f"CAM {self.camera_id.upper()} [{sync_label}] - F:{frame_id} - {time.strftime('%H:%M:%S')}",
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (242, 208, 78),
            1,
            cv2.LINE_AA,
        )
        _, raw_buf = cv2.imencode(".jpg", raw_osd, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        raw_bytes = raw_buf.tobytes() if _ else None
        if raw_bytes is not None:
            with self._lock:
                self.cached_raw_jpeg = raw_bytes

        # 2. YOLO + ByteTrack Inference
        yolo_frame = resized_raw.copy()
        model = self.model or _get_yolo_model()
        active_veh = None
        top_motion_score = -1.0
        num_detected = 0

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
                yolo_frame = results.plot()

                ocr_runs_this_frame = 0
                if results.boxes is not None and len(results.boxes) > 0:
                    num_detected = len(results.boxes)
                    sorted_boxes = sorted(
                        results.boxes,
                        key=lambda b: (
                            (float(b.xyxy[0][2] - b.xyxy[0][0]) * float(b.xyxy[0][3] - b.xyxy[0][1]))
                            * float(b.conf[0] if b.conf is not None else 0.5)
                        ),
                        reverse=True,
                    )
                    for box in sorted_boxes:
                        cls_id = int(box.cls[0]) if box.cls is not None else 2
                        if cls_id not in [2, 3, 5, 7]:
                            continue

                        if box.id is None:
                            continue

                        matched_id = int(box.id[0])
                        conf = float(box.conf[0]) if box.conf is not None else 0.85
                        bbox = [int(v) for v in box.xyxy[0].tolist()]
                        x1, y1, x2, y2 = bbox
                        cx = (x1 + x2) / 2.0
                        cy = (y1 + y2) / 2.0

                        veh_crop = resized_raw[max(0, y1):min(resized_raw.shape[0], y2), max(0, x1):min(resized_raw.shape[1], x2)]
                        color_detected = _detect_crop_color(veh_crop)
                        cls_type = "CAR" if cls_id == 2 else "TRUCK" if cls_id == 7 else "BUS" if cls_id == 5 else "MOTORCYCLE"

                        current_time_str = time.strftime("%I:%M:%S %p")
                        if matched_id in self.vehicle_tracks:
                            trk = self.vehicle_tracks[matched_id]
                            trk["cx"] = cx
                            trk["cy"] = cy
                            trk["frames"] += 1
                            trk["last_seen"] = frame_id
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
                                "last_seen": frame_id,
                                "crops": [],
                                "best_crop": veh_crop.copy() if (veh_crop is not None and veh_crop.size > 0 and veh_crop.shape[0] >= 24 and veh_crop.shape[1] >= 24) else None,
                                "best_crop_score": 0.0,
                                "obs_uuid": None,
                                "has_embedding": False,
                                "last_embedded_score": 0.0,
                                "persisted": False,
                                "finalized_status": False,
                                "ocr_attempts": 0,
                                "last_ocr_frame": -999,
                                "plate_confirmed": False,
                                "ocr_success_count": 0,
                            }
                            trk = self.vehicle_tracks[matched_id]

                        # Score crop quality and maintain track's best crop
                        crop_score = 0.0
                        if veh_crop is not None and veh_crop.size > 0:
                            crop_score = score_crop_quality(
                                crop=veh_crop,
                                bbox=[x1, y1, x2, y2],
                                frame_shape=resized_raw.shape,
                                conf=conf,
                            )
                            if crop_score > trk.get("best_crop_score", 0.0) or trk.get("best_crop") is None:
                                if veh_crop.shape[0] >= 24 and veh_crop.shape[1] >= 24:
                                    trk["best_crop"] = veh_crop.copy()
                                    trk["best_crop_score"] = crop_score

                        # Collect high-quality vehicle crops for track appearance embedding
                        if "crops" not in trk:
                            trk["crops"] = []
                        if len(trk["crops"]) < settings.APPEARANCE_MAX_TRACK_SAMPLES:
                            if veh_crop is not None and veh_crop.size > 0:
                                if veh_crop.shape[0] >= settings.APPEARANCE_MIN_CROP_SIZE and veh_crop.shape[1] >= settings.APPEARANCE_MIN_CROP_SIZE:
                                    trk["crops"].append(veh_crop.copy())

                        # Stabilize vehicle attributes with majority voting across frames
                        stable_type = max(set(trk["types"]), key=trk["types"].count)
                        stable_color = max(set(trk["colors"]), key=trk["colors"].count)

                        obs_id_str = f"TRACE-{self.camera_id.upper()}-{matched_id:03d}"
                        track_id_str = f"TRK-{matched_id:03d}"                        # Plate OCR: Non-blocking background worker dispatch
                        track_ocr_attempts = trk.get("ocr_attempts", 0)
                        last_ocr = trk.get("last_ocr_frame", -999)
                        is_confirmed = trk.get("plate_confirmed", False)
                        has_enough_reads = trk.get("ocr_success_count", 0) >= 3
                        in_ocr = trk.get("ocr_in_flight", False)

                        should_ocr = (
                            ocr_runs_this_frame < 2
                            and not is_confirmed
                            and not has_enough_reads
                            and not in_ocr
                            and track_ocr_attempts < 8
                            and veh_crop.size > 0
                            and veh_crop.shape[1] >= 65
                            and veh_crop.shape[0] >= 45
                            and (frame_id - last_ocr >= 10 or is_new)
                        )

                        if should_ocr:
                            trk["last_ocr_frame"] = frame_id
                            trk["ocr_attempts"] = track_ocr_attempts + 1
                            trk["ocr_in_flight"] = True
                            ocr_runs_this_frame += 1
                            plate_crop = extract_plate_crop(veh_crop)
                            if plate_crop is not None and plate_crop.size > 0:
                                self._bg_executor.submit(
                                    self._async_ocr_task,
                                    matched_id,
                                    track_id_str,
                                    frame_id,
                                    plate_crop.copy(),
                                )

                        fused_record = self.fusion.fuse_track(
                            camera_id=self.camera_id,
                            track_id=track_id_str,
                            vehicle_type=stable_type,
                            vehicle_colour=stable_color,
                        )

                        plate_text = fused_record.get("fused_plate_text", "NOT READ")
                        ocr_conf = fused_record.get("fused_confidence")
                        ocr_status = "READ" if plate_text != "NOT READ" else "NOT READ"

                        # Update recent detections list
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

                        # Persist observation to DB (Asynchronously on background thread to never stall video FPS)
                        if self._db_engine and not is_db_in_backoff():
                            if not trk.get("persisted", False) and not trk.get("persist_in_flight", False):
                                if is_moving or trk["frames"] >= 5:
                                    trk["persist_in_flight"] = True
                                    best_crop_copy = trk.get("best_crop").copy() if trk.get("best_crop") is not None else None
                                    crops_copy = [c.copy() for c in trk.get("crops", [])]
                                    self._bg_executor.submit(
                                        self._async_persist_observation,
                                        matched_id,
                                        track_id_str,
                                        stable_type,
                                        stable_color,
                                        plate_text,
                                        ocr_conf,
                                        list(fused_record.get("reads_history", [])),
                                        best_crop_copy,
                                        crops_copy,
                                        trk.get("best_crop_score", 0.0),
                                    )
                            elif trk.get("obs_uuid") and settings.APPEARANCE_REID_ENABLED and not trk.get("emb_in_flight", False):
                                # Continuous upgrade: If track lacks embedding or current crop is significantly better (+0.15 score)
                                needs_initial_emb = not trk.get("has_embedding", False)
                                is_significant_upgrade = crop_score > (trk.get("last_embedded_score", 0.0) + 0.15)
                                if (needs_initial_emb or is_significant_upgrade) and veh_crop is not None and veh_crop.size > 0:
                                    trk["emb_in_flight"] = True
                                    self._bg_executor.submit(
                                        self._async_upgrade_embedding,
                                        matched_id,
                                        trk["obs_uuid"],
                                        veh_crop.copy(),
                                        crop_score,
                                    )

                        box_w = max(1, x2 - x1)
                        box_h = max(1, y2 - y1)
                        box_area = box_w * box_h
                        motion_score = (1000.0 if is_moving else 0.0) + disp + (conf * 10.0) + (box_area / 1000.0)
                        if motion_score > top_motion_score:
                            top_motion_score = motion_score
                            active_veh = {
                                "camera_id": self.camera_id,
                                "camera_name": self.name,
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

                    # Finalize tracks that have exited the field of view (not seen in 30 frames)
                    stale_ids = [
                        tid for tid, t in self.vehicle_tracks.items()
                        if (frame_id - t.get("last_seen", 0) > 30 and not t.get("finalized_status", False))
                    ]
                    for st_id in stale_ids:
                        t = self.vehicle_tracks[st_id]
                        t["finalized_status"] = True
                        if (
                            t.get("persisted")
                            and not t.get("has_embedding")
                            and t.get("obs_uuid")
                            and self._db_engine
                            and not is_db_in_backoff()
                            and not t.get("emb_in_flight", False)
                        ):
                            t["emb_in_flight"] = True
                            best_crop_copy = t.get("best_crop").copy() if t.get("best_crop") is not None else None
                            self._bg_executor.submit(
                                self._async_finalize_embedding,
                                st_id,
                                t["obs_uuid"],
                                best_crop_copy,
                            )

                    # Prune stale tracks when tracking table grows too large
                    if len(self.vehicle_tracks) > 300:
                        stale = [
                            tid for tid, trk in self.vehicle_tracks.items()
                            if frame_id - trk.get("last_seen", 0) > 200
                        ]
                        for st in stale:
                            self.vehicle_tracks.pop(st, None)

            except Exception as e:
                pass

        cv2.putText(
            yolo_frame,
            f"CAM {self.camera_id.upper()} [AI LIVE] - {time.strftime('%H:%M:%S')}",
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 242, 254),
            1,
            cv2.LINE_AA,
        )
        _, yolo_buf = cv2.imencode(".jpg", yolo_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        yolo_bytes = yolo_buf.tobytes() if _ else None

        with self._lock:
            if (stop_event is not None and (stop_event.is_set() or self._generation != generation)) or not self._running:
                return
            if raw_bytes is not None:
                self.cached_raw_jpeg = raw_bytes
            if yolo_bytes is not None:
                self.cached_yolo_jpeg = yolo_bytes
            if active_veh is not None:
                self.active_vehicle_data.update(active_veh)
            self.active_vehicle_data["recent_detections"] = list(self.recent_detections)
            self.current_detection_count = num_detected
            self.current_frame_idx = frame_id
            self._frame_cond.notify_all()

    def _async_ocr_task(self, matched_id: int, track_id_str: str, frame_id: int, plate_crop: Optional[np.ndarray]):
        """Execute PaddleOCR in background thread pool without stalling video rendering."""
        try:
            if plate_crop is None or plate_crop.size == 0:
                return
            ocr_res = read_plate_image(plate_crop, min_confidence=0.20)
            if ocr_res:
                best_ocr = max(ocr_res, key=lambda x: x["confidence"])
                with self._lock:
                    trk = self.vehicle_tracks.get(matched_id)
                    if trk:
                        trk["ocr_success_count"] = trk.get("ocr_success_count", 0) + 1
                        if best_ocr["confidence"] >= 0.85:
                            trk["plate_confirmed"] = True
                self.fusion.add_ocr_read(
                    camera_id=self.camera_id,
                    track_id=track_id_str,
                    frame_id=frame_id,
                    raw_text=best_ocr["raw_text"],
                    confidence=best_ocr["confidence"],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.debug(f"Async OCR error for {track_id_str}: {e}")
        finally:
            with self._lock:
                trk = self.vehicle_tracks.get(matched_id)
                if trk:
                    trk["ocr_in_flight"] = False

    def _async_persist_observation(
        self,
        matched_id: int,
        track_id_str: str,
        vehicle_type: str,
        vehicle_colour: str,
        plate_text: str,
        ocr_conf: Optional[float],
        ocr_reads: list,
        best_crop: Optional[np.ndarray],
        crops_samples: list,
        crop_score: float,
    ):
        """Extract appearance embedding and persist vehicle observation asynchronously."""
        try:
            appearance_embedding = None
            emb_status = "pending"
            emb_reason = None

            if settings.APPEARANCE_REID_ENABLED:
                try:
                    from app.modules.appearance import get_appearance_extractor
                    extractor = get_appearance_extractor()
                    if best_crop is not None:
                        appearance_embedding, emb_reason = extractor.extract_with_reason(
                            best_crop, min_size=settings.APPEARANCE_MIN_CROP_SIZE
                        )
                    elif crops_samples:
                        appearance_embedding = extractor.extract_track_embedding(crops_samples)
                        if appearance_embedding is None:
                            emb_reason = "track_crops_extraction_failed"
                    else:
                        emb_reason = "crop_pending_better_frame"

                    if appearance_embedding is not None:
                        emb_status = "complete"
                        emb_reason = None
                except Exception as emb_err:
                    appearance_embedding = None
                    emb_reason = f"inference_error: {str(emb_err)[:50]}"
            else:
                emb_status = "failed"
                emb_reason = "appearance_reid_disabled"

            from sqlalchemy.orm import Session
            with Session(self._db_engine) as session:
                db_obs = persist_fused_observation(
                    session=session,
                    camera_id_str=self.camera_id,
                    track_id=track_id_str,
                    captured_at=datetime.now(timezone.utc),
                    fused_plate_text=plate_text,
                    fused_confidence=ocr_conf,
                    vehicle_type=vehicle_type,
                    vehicle_colour=vehicle_colour,
                    ocr_reads=ocr_reads,
                    appearance_embedding=appearance_embedding,
                    embedding_status=emb_status,
                    embedding_failure_reason=emb_reason,
                    embedding_attempts=1,
                )
                if db_obs:
                    with self._lock:
                        trk = self.vehicle_tracks.get(matched_id)
                        if trk:
                            trk["persisted"] = True
                            trk["obs_uuid"] = db_obs.observation_id
                            self.persisted_tracks.add(matched_id)
                            if appearance_embedding is not None:
                                trk["has_embedding"] = True
                                trk["last_embedded_score"] = crop_score
                    try:
                        from app.modules.identity import match_new_observation
                        match_new_observation(session, db_obs)
                    except Exception as fuse_err:
                        logger.debug(f"Online identity fusion error: {fuse_err}")
        except Exception as db_err:
            record_db_error(str(db_err))
        finally:
            with self._lock:
                trk = self.vehicle_tracks.get(matched_id)
                if trk:
                    trk["persist_in_flight"] = False

    def _async_upgrade_embedding(self, matched_id: int, obs_uuid: str, veh_crop: np.ndarray, crop_score: float):
        """Extract upgraded appearance embedding on background worker thread."""
        try:
            from app.modules.appearance import get_appearance_extractor
            extractor = get_appearance_extractor()
            upg_emb, upg_reason = extractor.extract_with_reason(veh_crop, min_size=settings.APPEARANCE_MIN_CROP_SIZE)
            if upg_emb is not None:
                from sqlalchemy.orm import Session
                with Session(self._db_engine) as session:
                    upsert_observation_embedding(
                        session=session,
                        observation_id=obs_uuid,
                        appearance_embedding=upg_emb,
                        embedding_status="complete",
                        embedding_failure_reason=None,
                    )
                with self._lock:
                    trk = self.vehicle_tracks.get(matched_id)
                    if trk:
                        trk["has_embedding"] = True
                        trk["last_embedded_score"] = crop_score
        except Exception as upg_err:
            logger.debug(f"Async embedding upgrade error: {upg_err}")
        finally:
            with self._lock:
                trk = self.vehicle_tracks.get(matched_id)
                if trk:
                    trk["emb_in_flight"] = False

    def _async_finalize_embedding(self, matched_id: int, obs_uuid: str, best_crop: Optional[np.ndarray]):
        """Finalize embedding for exited vehicle track on background worker thread."""
        try:
            fin_emb = None
            fin_reason = "crop_too_small_or_empty"
            if best_crop is not None:
                from app.modules.appearance import get_appearance_extractor
                fin_emb, fin_reason = get_appearance_extractor().extract_with_reason(
                    best_crop, min_size=settings.APPEARANCE_MIN_CROP_SIZE
                )
            from sqlalchemy.orm import Session
            with Session(self._db_engine) as session:
                if fin_emb is not None:
                    upsert_observation_embedding(session, obs_uuid, fin_emb, "complete", None)
                    with self._lock:
                        trk = self.vehicle_tracks.get(matched_id)
                        if trk:
                            trk["has_embedding"] = True
                else:
                    upsert_observation_embedding(
                        session, obs_uuid, None, "failed", fin_reason or "track_exited_no_valid_crop"
                    )
        except Exception as fin_err:
            logger.debug(f"Async finalize embedding error: {fin_err}")
        finally:
            with self._lock:
                trk = self.vehicle_tracks.get(matched_id)
                if trk:
                    trk["emb_in_flight"] = False

    def get_frame(self, annotate: bool = False, annotate_yolo: bool = False) -> Optional[bytes]:
        with self._lock:
            if annotate or annotate_yolo:
                return self.cached_yolo_jpeg or self.cached_raw_jpeg
            return self.cached_raw_jpeg

    def get_next_frame(self, last_frame_idx: int, annotate: bool = False, timeout: float = 0.2) -> Tuple[Optional[bytes], int]:
        """Thread-safe condition-driven frame waiter that eliminates polling, duplicate frames, and video stutter."""
        with self._frame_cond:
            if self.current_frame_idx == last_frame_idx or self.current_frame_idx <= 0:
                self._frame_cond.wait(timeout=timeout)
            frame = (self.cached_yolo_jpeg or self.cached_raw_jpeg) if annotate else self.cached_raw_jpeg
            return frame, self.current_frame_idx

    def get_active_vehicle(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.active_vehicle_data)

    def get_live_scan_count(self) -> int:
        """Return dynamic count of active vehicles currently in this camera's view."""
        with self._lock:
            if not self.enabled or self.status_label in ["DISABLED", "FAILED", "OFFLINE"]:
                return 0
            active_tracks = sum(
                1 for t in self.vehicle_tracks.values()
                if (self.current_frame_idx - t.get("last_seen", 0) <= 25) and not t.get("finalized_status", False)
            )
            return max(getattr(self, "current_detection_count", 0), active_tracks)


class CameraScenarioManager:
    """Singleton manager coordinating all TRACE camera inputs, dynamic hot-swapping, and playback."""

    def __init__(self):
        self._lock = threading.Lock()
        self.controller = CameraPlaybackController()
        self.cameras: Dict[str, ManagedCameraWorker] = {}
        self._bg_timer_thread = threading.Thread(target=self._clock_tick_loop, daemon=True)
        self._bg_timer_running = True

        # Load persisted or default configuration
        self._init_cameras()
        self._bg_timer_thread.start()

    def get_total_active_scans(self) -> int:
        """Return total active vehicle scans across all camera feeds."""
        with self._lock:
            return sum(cam.get_live_scan_count() for cam in self.cameras.values())

    def _clock_tick_loop(self):
        """Continuously tick master scenario clock."""
        while self._bg_timer_running:
            self.controller.tick()
            time.sleep(0.05)

    def _init_cameras(self):
        """Initialize cameras from data/camera_config.json or default CityFlow S04 cameras."""
        config_path = _get_config_path()
        saved_configs: Dict[str, Any] = {}

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    saved_configs = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load {config_path}: {e}")

        # Default camera setup if no config file exists
        default_defs = [
            {"camera_id": "c020", "name": "Camera 020", "source_type": "video", "source_path": "footage/c020/vdo.avi", "scenario": "S04", "fps": 10.0, "sync_offset_s": 25.905, "enabled": True},
            {"camera_id": "c023", "name": "Camera 023", "source_type": "video", "source_path": "footage/c023/vdo.avi", "scenario": "S04", "fps": 10.0, "sync_offset_s": 45.716, "enabled": True},
            {"camera_id": "c029", "name": "Camera 029", "source_type": "video", "source_path": "footage/c029/vdo.avi", "scenario": "S04", "fps": 10.0, "sync_offset_s": 125.788, "enabled": True},
            {"camera_id": "c035", "name": "Camera 035", "source_type": "video", "source_path": "footage/c035/vdo.avi", "scenario": "S04", "fps": 10.0, "sync_offset_s": 165.568, "enabled": True},
        ]

        # Load sync mode from saved config
        if saved_configs.get("sync_mode"):
            self.controller.sync_mode = saved_configs["sync_mode"]

        cameras_data = saved_configs.get("cameras", {})
        for default_item in default_defs:
            cid = default_item["camera_id"]
            cfg = cameras_data.get(cid, default_item)
            self.cameras[cid] = ManagedCameraWorker(cid, cfg, self.controller)

    def save_configuration(self):
        """Persist current camera configuration and playback settings to data/camera_config.json."""
        config_path = _get_config_path()
        try:
            data = {
                "sync_mode": self.controller.sync_mode,
                "loop_scenario": self.controller.loop_scenario,
                "cameras": {cid: worker.to_dict() for cid, worker in self.cameras.items()},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist camera config to {config_path}: {e}")

    def list_cameras(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [cam.to_dict() for cam in self.cameras.values()]

    def get_camera(self, camera_id: str) -> Optional[ManagedCameraWorker]:
        clean_id = camera_id.lower().strip()
        alias_map = {"cam-13": "c020", "cam-14": "c023", "cam-15": "c029", "cam-16": "c035"}
        clean_id = alias_map.get(clean_id, clean_id)
        with self._lock:
            return self.cameras.get(clean_id)

    def update_camera_source(
        self,
        camera_id: str,
        source_path: str,
        source_type: str = "video",
        fps: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Safely hot-swap the camera source (Video or Image) without application restart."""
        clean_id = camera_id.lower().strip()
        worker = self.get_camera(clean_id)
        if not worker:
            raise ValueError(f"Camera '{camera_id}' not found")

        # 1. Stop existing worker
        worker.stop()

        # 2. Detect scenario & sync offset for the new source
        sync_meta = load_cityflow_sync_metadata()
        detected_scenario = "General"
        detected_offset = 0.0

        for sc, sc_cams in sync_meta.items():
            if sc.lower() in source_path.lower():
                detected_scenario = sc
                break
            elif clean_id in sc_cams:
                detected_scenario = sc
                break

        if clean_id in sync_meta.get(detected_scenario, {}):
            detected_offset = sync_meta[detected_scenario][clean_id].get("start_timestamp_s", 0.0)

        # 3. Update configuration and purge old video state
        with worker._lock:
            worker.source_path = source_path
            worker.source_type = source_type.lower()
            worker.scenario = detected_scenario
            worker.sync_offset_s = detected_offset
            if fps and fps > 0:
                worker.fps = fps
            worker.current_frame_idx = 0
            worker.cached_raw_jpeg = None
            worker.cached_yolo_jpeg = None
            worker.vehicle_tracks.clear()
            worker.recent_detections.clear()
            worker.persisted_tracks.clear()
            worker.fusion = TemporalOCRFusion()
            worker.active_vehicle_data = {
                "camera_id": worker.camera_id,
                "camera_name": worker.name,
                "observation_id": f"TRACE-{worker.camera_id.upper()}-01",
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

        # 4. Restart worker
        worker.start()
        self.save_configuration()

        logger.info(f"[CAMERA UPDATE] {clean_id} switched to {source_type}: '{source_path}' (scenario={detected_scenario}, offset={detected_offset}s)")
        return worker.to_dict()

    def set_camera_enabled(self, camera_id: str, enabled: bool) -> Dict[str, Any]:
        worker = self.get_camera(camera_id)
        if not worker:
            raise ValueError(f"Camera '{camera_id}' not found")
        with worker._lock:
            worker.enabled = bool(enabled)
            worker.status_label = "PROCESSING" if worker.enabled else "DISABLED"
        self.save_configuration()
        return worker.to_dict()

    def update_camera_settings(
        self,
        camera_id: str,
        name: Optional[str] = None,
        fps: Optional[float] = None,
        sync_offset_s: Optional[float] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update runtime camera parameters."""
        worker = self.get_camera(camera_id)
        if not worker:
            raise ValueError(f"Camera '{camera_id}' not found")
        with worker._lock:
            if name is not None:
                worker.name = name
            if fps is not None and fps > 0:
                worker.fps = float(fps)
            if sync_offset_s is not None:
                worker.sync_offset_s = float(sync_offset_s)
            if enabled is not None:
                worker.enabled = bool(enabled)
                worker.status_label = "PROCESSING" if worker.enabled else "DISABLED"
        self.save_configuration()
        return worker.to_dict()

    def get_camera_preview(self, camera_id: str) -> Dict[str, Any]:
        """Return an instant snapshot frame and current camera status."""
        worker = self.get_camera(camera_id)
        if not worker:
            raise ValueError(f"Camera '{camera_id}' not found")
        frame_bytes = worker.get_frame(annotate=True) or worker.get_frame(annotate=False)
        b64 = base64.b64encode(frame_bytes).decode("utf-8") if frame_bytes else ""
        return {
            "camera_id": worker.camera_id,
            "name": worker.name,
            "status": worker.status_label,
            "source_type": worker.source_type,
            "source_path": worker.source_path,
            "current_frame_idx": worker.current_frame_idx,
            "total_frames": worker.total_frames,
            "preview_b64": b64,
        }

    def debug_test_image(self, image_path: str) -> Dict[str, Any]:
        """Execute full production perception pipeline on an image and return visual crops for inspection."""
        data_dir = _get_project_data_dir()
        p = Path(image_path)
        if not p.is_absolute():
            candidate = data_dir / image_path
            if not candidate.exists():
                candidate = data_dir / "TN" / image_path
            if not candidate.exists():
                candidate = data_dir / "footage" / image_path
            p = candidate

        if not p.exists():
            raise FileNotFoundError(f"Image not found at '{image_path}'")

        img = cv2.imread(str(p))
        if img is None:
            raise ValueError(f"Could not decode image at '{p}'")

        h, w = img.shape[:2]
        model = _get_yolo_model()
        if model is None:
            raise RuntimeError("YOLO model not loaded")

        results = model(img, conf=0.18, classes=[2, 3, 5, 7], verbose=False)[0]
        annotated = results.plot()

        # Find best vehicle detection (prioritize primary / foreground vehicle by area * conf)
        best_box = None
        best_conf = -1.0
        best_score = -1.0
        vtype = "CAR"
        vbbox = [0, 0, w, h]

        if results.boxes is not None and len(results.boxes) > 0:
            for b in results.boxes:
                cls_id = int(b.cls[0]) if b.cls is not None else 2
                if cls_id in [2, 3, 5, 7]:
                    conf = float(b.conf[0])
                    xyxy = [int(v) for v in b.xyxy[0].tolist()]
                    box_w = max(1, xyxy[2] - xyxy[0])
                    box_h = max(1, xyxy[3] - xyxy[1])
                    score = (box_w * box_h) * conf
                    if score > best_score:
                        best_score = score
                        best_conf = conf
                        best_box = b
                        vtype = "CAR" if cls_id == 2 else "TRUCK" if cls_id == 7 else "BUS" if cls_id == 5 else "MOTORCYCLE"
                        vbbox = xyxy

        x1, y1, x2, y2 = vbbox
        veh_crop = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if veh_crop.size == 0:
            veh_crop = img

        color_detected = _detect_crop_color(veh_crop)
        plate_crop = extract_plate_crop(veh_crop)
        ocr_res = read_plate_image(plate_crop, min_confidence=0.20)

        # Fallback to OCR on vehicle crop if plate crop yielded no detection
        if not ocr_res:
            ocr_res = read_plate_image(veh_crop, min_confidence=0.20)
            if ocr_res:
                best_item = max(ocr_res, key=lambda x: x["confidence"])
                box = best_item.get("bbox")
                if box and len(box) == 4:
                    xs = [pt[0] for pt in box]
                    ys = [pt[1] for pt in box]
                    plate_crop = extract_plate_crop(
                        veh_crop,
                        bbox=[int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                    )

        best_plate = "NOT READ"
        ocr_conf = None
        if ocr_res:
            best_item = max(ocr_res, key=lambda x: x["confidence"])
            best_plate = best_item["normalized_text"]
            ocr_conf = round(best_item["confidence"], 3)

        def _to_b64(cv_img: np.ndarray) -> str:
            if cv_img is None or cv_img.size == 0:
                return ""
            _, b = cv2.imencode(".jpg", cv_img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            return base64.b64encode(b.tobytes()).decode("utf-8") if _ else ""

        return {
            "image_path": str(p),
            "dimensions": f"{w}x{h}",
            "vehicle_detected": best_box is not None,
            "vehicle_type": vtype,
            "vehicle_confidence": round(best_conf, 3) if best_conf > 0 else None,
            "vehicle_colour": color_detected,
            "plate_detected": best_plate != "NOT READ",
            "plate_number": best_plate,
            "ocr_confidence": ocr_conf,
            "original_image_b64": _to_b64(img),
            "yolo_annotated_b64": _to_b64(annotated),
            "vehicle_crop_b64": _to_b64(veh_crop),
            "plate_crop_b64": _to_b64(plate_crop),
        }


_GLOBAL_CAMERA_MANAGER: Optional[CameraScenarioManager] = None
_INIT_LOCK = threading.Lock()


def get_camera_manager() -> CameraScenarioManager:
    """Singleton getter for the global CameraScenarioManager."""
    global _GLOBAL_CAMERA_MANAGER
    with _INIT_LOCK:
        if _GLOBAL_CAMERA_MANAGER is None:
            _GLOBAL_CAMERA_MANAGER = CameraScenarioManager()
        return _GLOBAL_CAMERA_MANAGER
