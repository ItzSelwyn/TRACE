"""Layer 1 — Perception Module: Unified Runtime Camera Input, Playback, and Scenario Synchronization Manager."""

from __future__ import annotations

import base64
import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from app.config import settings
from app.modules.perception.normalization import normalize_plate_text
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.persistence import is_db_in_backoff, persist_fused_observation, record_db_error
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
        self._thread: Optional[threading.Thread] = None

        # Configuration properties
        self.name: str = config.get("name", f"Camera {self.camera_id.upper()}")
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
            if not self._running:
                self._running = True
                self._thread = threading.Thread(target=self._worker_loop, daemon=True)
                self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            sync_active = (self.controller.sync_mode == "synchronized")
            return {
                "camera_id": self.camera_id,
                "name": self.name,
                "source_type": self.source_type,
                "source_path": self.source_path,
                "scenario": self.scenario,
                "fps": self.fps,
                "enabled": self.enabled,
                "sync_offset_s": self.sync_offset_s,
                "frame_count": self.frame_count,
                "total_frames": self.total_frames,
                "status": "DISABLED" if not self.enabled else self.status_label,
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

    def _worker_loop(self):
        """Dedicated execution loop for video or image source."""
        resolved_path = self._resolve_full_path()
        model = _get_yolo_model()

        # Handle Still Image source
        if self.source_type == "image":
            self._run_image_loop(resolved_path)
            return

        # Handle Video source
        if not resolved_path.exists():
            with self._lock:
                self.status_label = "OFFLINE"
            return

        cap = cv2.VideoCapture(str(resolved_path))
        if not cap.isOpened():
            with self._lock:
                self.status_label = "FAILED"
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or (self.frame_count or 9999)
        self.frame_count = total_frames
        self.total_frames = total_frames
        video_fps = cap.get(cv2.CAP_PROP_FPS) or self.fps or 10.0

        last_rendered_frame_idx = -1

        while self._running:
            loop_start = time.time()

            if not self.enabled:
                with self._lock:
                    self.status_label = "DISABLED"
                time.sleep(0.2)
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
                        time.sleep(0.05)
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
                time.sleep(0.08)
                continue

            if play_state == "stopped":
                time.sleep(0.08)
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
                        # Reset video position so when entry time arrives, it starts at frame 0
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        last_rendered_frame_idx = -1
                        self.current_frame_idx = 0
                    time.sleep(0.05)
                    continue

                if last_rendered_frame_idx >= total_frames - 1:
                    # Reached end of scenario footage -> hold cleanly on last frame
                    with self._lock:
                        self.status_label = "SOURCE ENDED"
                    time.sleep(0.1)
                    continue

                with self._lock:
                    self.status_label = "PROCESSING"
            else:
                # Independent Testing Mode: loop independently at native FPS
                with self._lock:
                    self.status_label = "SYNC DISABLED"

            # Sequential frame read — zero frame skipping during normal forward playback!
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
                    time.sleep(0.1)
                    continue

            if not ret or frame is None:
                time.sleep(0.05)
                continue

            last_rendered_frame_idx += 1
            self.current_frame_idx = last_rendered_frame_idx
            if sync_mode != "synchronized":
                self.current_local_time_s = round(self.current_frame_idx / self.fps, 2)

            # Process frame through perception pipeline
            self._process_and_cache_frame(frame, self.current_frame_idx)

            # Throttle loop interval subtracting actual elapsed inference time
            target_fps = max(1.0, self.fps * self.controller.playback_speed)
            target_interval = 1.0 / target_fps
            elapsed = time.time() - loop_start
            sleep_time = target_interval - elapsed

            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()

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

    def _run_image_loop(self, image_path: Path):
        """Execution loop for Still Image camera sources."""
        if not image_path.exists():
            with self._lock:
                self.status_label = "IMAGE NOT FOUND"
            return

        img = cv2.imread(str(image_path))
        if img is None:
            with self._lock:
                self.status_label = "FAILED"
            return

        frame_idx = 0
        while self._running:
            if not self.enabled:
                with self._lock:
                    self.status_label = "DISABLED"
                time.sleep(0.3)
                continue

            with self._lock:
                self.status_label = "IMAGE ACTIVE"

            frame_idx += 1
            self.current_frame_idx = frame_idx
            self._process_and_cache_frame(img.copy(), frame_idx)
            time.sleep(1.0 / max(1.0, self.fps))

    def _process_and_cache_frame(self, frame: np.ndarray, frame_id: int):
        """Run YOLOv8, ByteTrack, Plate Localization, PaddleOCR, and caching on the frame."""
        resized_raw = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)

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

        # 2. YOLO + ByteTrack Inference
        yolo_frame = resized_raw.copy()
        model = self.model or _get_yolo_model()
        active_veh = None
        top_motion_score = -1.0

        if model is not None:
            try:
                results = model.track(
                    resized_raw,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=0.25,
                    verbose=False,
                )[0]
                yolo_frame = results.plot()

                if results.boxes is not None and len(results.boxes) > 0:
                    for box in results.boxes:
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
                            }
                            trk = self.vehicle_tracks[matched_id]

                        # Stabilize vehicle attributes with majority voting across frames
                        stable_type = max(set(trk["types"]), key=trk["types"].count)
                        stable_color = max(set(trk["colors"]), key=trk["colors"].count)

                        obs_id_str = f"TRACE-{self.camera_id.upper()}-{matched_id:03d}"
                        track_id_str = f"TRK-{matched_id:03d}"

                        # Plate OCR
                        if (is_moving or is_new or frame_id % 15 == 0) and veh_crop.size > 0:
                            try:
                                plate_crop = extract_plate_crop(veh_crop)
                                ocr_res = read_plate_image(plate_crop, min_confidence=0.20)
                                if not ocr_res and veh_crop.shape[0] < 450 and veh_crop.shape[1] < 650:
                                    ocr_res = read_plate_image(veh_crop, min_confidence=0.20)
                                if ocr_res:
                                    best_ocr = max(ocr_res, key=lambda x: x["confidence"])
                                    self.fusion.add_ocr_read(
                                        camera_id=self.camera_id,
                                        track_id=track_id_str,
                                        frame_id=frame_id,
                                        raw_text=best_ocr["raw_text"],
                                        confidence=best_ocr["confidence"],
                                        timestamp=datetime.now(timezone.utc).isoformat(),
                                    )
                            except Exception:
                                pass

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

                        # Persist observation to DB
                        if self._db_engine and not is_db_in_backoff() and matched_id not in self.persisted_tracks:
                            if is_moving or trk["frames"] >= 5:
                                from sqlalchemy.orm import Session
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

                        motion_score = (1000.0 if is_moving else 0.0) + disp + (conf * 10)
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
            if raw_bytes is not None:
                self.cached_raw_jpeg = raw_bytes
            if yolo_bytes is not None:
                self.cached_yolo_jpeg = yolo_bytes
            if active_veh is not None:
                self.active_vehicle_data.update(active_veh)
            self.active_vehicle_data["recent_detections"] = list(self.recent_detections)

    def get_frame(self, annotate: bool = False, annotate_yolo: bool = False) -> Optional[bytes]:
        with self._lock:
            if annotate or annotate_yolo:
                return self.cached_yolo_jpeg or self.cached_raw_jpeg
            return self.cached_raw_jpeg

    def get_active_vehicle(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.active_vehicle_data)


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

        # 3. Update configuration
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

        results = model(img, conf=0.18, verbose=False)[0]
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
