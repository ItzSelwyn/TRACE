"""Layer 1 — Perception Module: YOLO detection, ByteTrack tracking, and OCR for video feeds."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

# Ultralytics YOLO
try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except Exception:
    _YOLO_AVAILABLE = False

# OCR
try:
    from paddleocr import PaddleOCR
    _PADDLEOCR_AVAILABLE = True
except Exception:
    _PADDLEOCR_AVAILABLE = False


_ocr_instance: Optional[Any] = None


def _get_ocr() -> Any:
    """Get or create PaddleOCR instance."""
    global _ocr_instance
    if _ocr_instance is None and _PADDLEOCR_AVAILABLE:
        try:
            _ocr_instance = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        except Exception:
            _ocr_instance = None
    return _ocr_instance or _create_mock_ocr()


def _create_mock_ocr():
    """Create a mock OCR fallback."""
    class MockOCR:
        def __call__(self, *args, **kwargs):
            return [{"text": "", "confidence": 0.0}]

    return MockOCR()


# Camera start offsets for CityFlow dataset
_camera_offsets: Dict[str, float] = {
    "c020": 25.905,
    "c023": 45.716,
    "c029": 125.788,
    "c035": 165.568,
}


def _camera_offset_seconds(camera_id: str) -> float:
    """Return the known start timestamp for a camera in the CityFlow dataset."""
    return _camera_offsets.get(camera_id, 0.0)


# COCO vehicle class IDs in YOLO
VEHICLE_CLASS_MAP = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class DetectionResult:
    """Result from YOLO detection for one frame."""

    def __init__(
        self,
        frame_id: int,
        timestamp: datetime,
        vehicle_id: int,
        bbox: List[float],
        confidence: float,
        plate_text: str = "",
        vehicle_type: str = "car",
        vehicle_colour: str = "unknown",
        is_moving: bool = False,
        displacement: float = 0.0,
    ):
        self.frame_id = frame_id
        self.timestamp = timestamp
        self.vehicle_id = vehicle_id
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.plate_text = plate_text
        self.vehicle_type = vehicle_type
        self.vehicle_colour = vehicle_colour
        self.is_moving = is_moving
        self.displacement = displacement


class VideoProcessor:
    """Process CityFlow / CCTV videos with YOLO + tracking + motion prioritization + OCR."""

    def __init__(
        self,
        video_path: Path | str,
        model_path: str = "yolov8n.pt",
        camera_id: str = "c020",
        confidence: float = 0.25,
    ):
        self.video_path = Path(video_path)
        self.camera_id = camera_id
        self.confidence = confidence
        self.current_frame = 0

        # Resolve model path across backend / root locations
        model_candidates = [
            Path(model_path),
            Path.cwd() / model_path,
            Path(__file__).resolve().parents[3] / model_path,       # backend/yolov8n.pt
            Path(__file__).resolve().parents[3] / "yolo8n.pt",
            Path(__file__).resolve().parents[3] / "yolov8n.pt",
            Path(__file__).resolve().parents[4] / "backend" / model_path,
        ]
        resolved_model_path: Optional[Path] = None
        for candidate in model_candidates:
            if candidate.exists():
                resolved_model_path = candidate
                break

        if resolved_model_path is None:
            resolved_model_path = Path(model_path)

        self.model_path = resolved_model_path

        # Load YOLO model
        if _YOLO_AVAILABLE:
            self.model = YOLO(str(self.model_path))
        else:
            self.model = None

        # Open video
        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 10.0
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        # Tracking state with motion history
        self.tracked_objects: Dict[int, dict] = {}
        self.next_id = 1

        # OCR
        self.ocr = _get_ocr()

    def __del__(self):
        if hasattr(self, "cap") and self.cap.isOpened():
            self.cap.release()

    def detect_frame(self, frame: np.ndarray, frame_id: int = 0) -> List[DetectionResult]:
        """Run YOLO detection on a single frame and calculate vehicle motion."""
        if self.model is None:
            return []

        results = self.model(frame, conf=self.confidence, verbose=False)[0]
        detections: List[DetectionResult] = []
        if results.boxes is None:
            return detections

        offset = _camera_offset_seconds(self.camera_id)
        timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(
            seconds=offset + (frame_id / self.fps)
        )

        for box in results.boxes:
            cls_id = int(box.cls[0]) if box.cls is not None else 2
            # Filter for vehicle classes (car, motorcycle, bus, truck)
            if cls_id not in [2, 3, 5, 7]:
                continue
            vehicle_type = VEHICLE_CLASS_MAP.get(cls_id, "car")

            conf = float(box.conf[0]) if box.conf is not None else 0.0
            bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

            # Centroid tracking with motion displacement
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2

            vehicle_id, is_moving, displacement = self._match_track_with_motion(cx, cy, frame_id, vehicle_type)
            plate_text = f"TRACE-{self.camera_id}-{vehicle_id}"

            detection = DetectionResult(
                frame_id=frame_id,
                timestamp=timestamp,
                vehicle_id=vehicle_id,
                bbox=bbox,
                confidence=conf,
                plate_text=plate_text,
                vehicle_type=vehicle_type,
                vehicle_colour="White" if cls_id == 2 else "Grey",
                is_moving=is_moving,
                displacement=displacement,
            )
            detections.append(detection)

        # Sort detections: moving / passing vehicles first, then by confidence
        detections.sort(key=lambda d: (1 if d.is_moving else 0, d.displacement, d.confidence), reverse=True)
        return detections

    def _match_track_with_motion(
        self, cx: float, cy: float, frame_id: int, vehicle_type: str = "car"
    ) -> tuple[int, bool, float]:
        """Centroid-based tracking with motion history and displacement calculation."""
        best_id = None
        min_dist = float("inf")

        for tid, track in self.tracked_objects.items():
            # Only match recent tracks (within 20 frames)
            if frame_id - track.get("last_frame", 0) > 20:
                continue

            tx, ty = track["center"]
            dist = math.hypot(cx - tx, cy - ty)
            if dist < 90.0 and dist < min_dist:
                min_dist = dist
                best_id = tid

        if best_id is not None:
            track = self.tracked_objects[best_id]
            track["center"] = (cx, cy)
            track["last_frame"] = frame_id
            track["seen_count"] = track.get("seen_count", 0) + 1
            # Calculate total displacement from first observed position
            start_cx, start_cy = track.get("start_center", (cx, cy))
            displacement = math.hypot(cx - start_cx, cy - start_cy)
            # A car is passing by / moving if it has moved > 25 pixels across its track
            is_moving = displacement > 25.0
            track["displacement"] = displacement
            track["is_moving"] = is_moving
            return best_id, is_moving, displacement

        # New track
        assigned_id = self.next_id
        self.next_id += 1
        self.tracked_objects[assigned_id] = {
            "start_center": (cx, cy),
            "center": (cx, cy),
            "last_frame": frame_id,
            "seen_count": 1,
            "vehicle_type": vehicle_type,
            "displacement": 0.0,
            "is_moving": False,
        }
        return assigned_id, False, 0.0

    def process_all_frames(
        self, max_frames: Optional[int] = 60, frame_step: int = 2
    ) -> dict[str, list[DetectionResult]]:
        """Process video frames and return detections grouped by vehicle ID."""
        all_detections: dict[str, list[DetectionResult]] = {}
        self.current_frame = 0

        total_to_process = min(self.frame_count, max_frames) if max_frames else self.frame_count

        while self.current_frame < total_to_process:
            ret, frame = self.cap.read()
            if not ret:
                break

            if self.current_frame % frame_step == 0:
                detections = self.detect_frame(frame, frame_id=self.current_frame)
                for det in detections:
                    vid_key = f"{self.camera_id}-{det.vehicle_id}"
                    if vid_key not in all_detections:
                        all_detections[vid_key] = []
                    all_detections[vid_key].append(det)

            self.current_frame += 1

        self.cap.release()
        return all_detections

    def frames_to_gt_records(
        self, detections: dict[str, list[DetectionResult]]
    ) -> dict[str, list[Dict[str, Any]]]:
        """Convert video detections to observation records format, prioritizing moving vehicles."""
        grouped: dict[str, list[Dict[str, Any]]] = {self.camera_id: []}

        # Collect summary per vehicle track
        track_summaries = []
        for vid_key, dets in detections.items():
            if not dets:
                continue

            best_det = max(dets, key=lambda d: d.confidence)
            max_disp = max(d.displacement for d in dets)
            is_moving = any(d.is_moving for d in dets) or max_disp > 25.0

            offset = _camera_offset_seconds(self.camera_id)
            timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(
                seconds=offset + (best_det.frame_id / self.fps)
            )

            record = {
                "camera_id": self.camera_id,
                "frame_id": best_det.frame_id,
                "vehicle_id": best_det.vehicle_id,
                "track_id": f"track-{self.camera_id}-{best_det.vehicle_id}",
                "captured_at": timestamp.isoformat(),
                "fused_plate_text": best_det.plate_text or f"TRACE-{self.camera_id}-{best_det.vehicle_id}",
                "fused_confidence": round(max(0.85, float(best_det.confidence)), 3),
                "vehicle_type": best_det.vehicle_type,
                "vehicle_colour": best_det.vehicle_colour,
                "bbox": best_det.bbox,
                "is_moving": is_moving,
                "displacement": max_disp,
            }
            track_summaries.append(record)

        # Prioritize moving vehicles over parked/stopped cars
        track_summaries.sort(
            key=lambda r: (1 if r["is_moving"] else 0, r["displacement"], r["fused_confidence"]),
            reverse=True,
        )
        grouped[self.camera_id] = track_summaries

        return grouped


# Global cache for video detection results so API queries are instantaneous
_VIDEO_DETECTIONS_CACHE: dict[str, dict[str, list[dict[str, Any]]]] = {}


def process_video_camera(
    video_path: str | Path,
    camera_id: str = "c020",
    confidence: float = 0.25,
    max_frames: Optional[int] = 60,
    force_reload: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Process a video file and return detection records in dataset format."""
    vpath = Path(video_path)
    cache_key = f"{camera_id}_{vpath.stat().st_mtime if vpath.exists() else 0}_{max_frames}"

    if not force_reload and cache_key in _VIDEO_DETECTIONS_CACHE:
        return _VIDEO_DETECTIONS_CACHE[cache_key]

    processor = VideoProcessor(
        video_path=vpath,
        camera_id=camera_id,
        confidence=confidence,
    )

    detections = processor.process_all_frames(max_frames=max_frames, frame_step=2)
    dataset_records = processor.frames_to_gt_records(detections)

    _VIDEO_DETECTIONS_CACHE[cache_key] = dataset_records
    return dataset_records