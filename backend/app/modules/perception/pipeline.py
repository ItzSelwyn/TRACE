"""Layer 1 — Perception Module: End-to-End Perception Pipeline with YOLO, ByteTrack, Plate Localization, PaddleOCR, Temporal Fusion, and PostgreSQL Persistence."""

from __future__ import annotations

import logging
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import cv2
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.modules.perception.normalization import normalize_plate_text
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.persistence import persist_fused_observation, resolve_camera_uuid
from app.modules.perception.plate_localizer import extract_plate_crop
from app.modules.perception.temporal_fusion import TemporalOCRFusion

logger = logging.getLogger("trace.perception.pipeline")

# COCO vehicle classes for YOLO
VEHICLE_CLASS_MAP = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


def _detect_crop_color(crop: np.ndarray) -> str:
    """Classify dominant vehicle body color using robust HSV/RGB analysis on painted panels.
    
    Returns one of: RED, ORANGE, YELLOW, GREEN, BLUE, WHITE, SILVER, BLACK.
    """
    if crop is None or crop.size == 0 or crop.shape[0] < 6 or crop.shape[1] < 6:
        return "SILVER"
    try:
        h, w = crop.shape[:2]
        # Focus on vehicle body: 25% to 75% height, 15% to 85% width
        # Excludes windshield/roof sky reflections and ground/tire dirt
        body = crop[int(h * 0.25):int(h * 0.75), int(w * 0.15):int(w * 0.85)]
        if body.size == 0:
            body = crop

        hsv = cv2.cvtColor(body, cv2.COLOR_BGR2HSV)
        H = hsv[:, :, 0]
        S = hsv[:, :, 1]
        V = hsv[:, :, 2]

        b, g, r = cv2.split(body)
        diff = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
        brightness = (r.astype(float) + g.astype(float) + b.astype(float)) / 3.0

        # Discard extreme highlights (sun glare) and extreme pitch black
        valid_mask = (V >= 25) & (V <= 250)
        if not np.any(valid_mask):
            valid_mask = np.ones_like(V, dtype=bool)

        # Identify chromatic paint pixels: high saturation and channel contrast
        chroma_mask = valid_mask & (S >= 55) & (diff >= 35) & (V >= 40)
        chroma_count = int(np.count_nonzero(chroma_mask))
        total_valid = int(np.count_nonzero(valid_mask))
        chroma_ratio = chroma_count / max(1, total_valid)

        if chroma_ratio >= 0.12 and chroma_count >= 15:
            # Chromatic vehicle: calculate dominant Hue using circular distance around 0/180
            chroma_h = H[chroma_mask]
            angles = chroma_h.astype(float) * (2.0 * np.pi / 180.0)
            mean_sin = np.mean(np.sin(angles))
            mean_cos = np.mean(np.cos(angles))
            mean_angle = np.arctan2(mean_sin, mean_cos)
            if mean_angle < 0:
                mean_angle += 2.0 * np.pi
            dom_h = mean_angle * (180.0 / (2.0 * np.pi))

            if dom_h < 10 or dom_h >= 165:
                return "RED"
            elif 10 <= dom_h < 24:
                return "ORANGE"
            elif 24 <= dom_h < 35:
                return "YELLOW"
            elif 35 <= dom_h < 85:
                return "GREEN"
            elif 85 <= dom_h < 140:
                return "BLUE"
            else:
                return "RED"

        # Achromatic vehicle: Black, White, Silver/Grey
        body_bright = brightness[valid_mask]
        med_bright = float(np.median(body_bright))
        p25 = float(np.percentile(body_bright, 25))
        p75 = float(np.percentile(body_bright, 75))

        # Black car: median brightness is low, or lower quartile is dark
        if med_bright < 70 or (p25 < 50 and med_bright < 85):
            return "BLACK"
        # White car: upper quartile is very bright and median is well above silver
        elif p75 > 190 or (med_bright > 165 and p75 > 180):
            return "WHITE"
        else:
            return "SILVER"
    except Exception:
        return "SILVER"


class PerceptionPipeline:
    """End-to-end perception pipeline for a single camera stream with PostgreSQL persistence."""

    def __init__(
        self,
        camera_id: str,
        yolo_model_path: str = "models/yolov8n.pt",
        confidence: float = 0.25,
        enable_ocr: bool = True,
        enable_db_persist: bool = True,
        enable_logging: bool = True,
    ):
        self.camera_id = camera_id
        self.confidence = confidence
        self.enable_ocr = enable_ocr
        self.enable_db_persist = enable_db_persist
        self.enable_logging = enable_logging

        # Initialize YOLO
        from ultralytics import YOLO
        
        root = Path(__file__).resolve().parents[4]
        candidates = [
            root / "backend" / "models" / "yolov8n.pt",
            root / "backend" / "models" / Path(yolo_model_path).name,
            root / "backend" / yolo_model_path,
            Path.cwd() / "models" / "yolov8n.pt",
            Path(yolo_model_path),
            root / "backend" / "yolov8n.pt",
            root / "backend" / "yolo8n.pt",
            Path.cwd() / yolo_model_path,
        ]
        resolved_path = next((c for c in candidates if c.exists()), Path(yolo_model_path))
        self.model = YOLO(str(resolved_path))

        # Temporal OCR Fusion engine
        self.fusion = TemporalOCRFusion()
        
        # Active vehicle state & track lifecycle
        self.current_observation: Optional[Dict[str, Any]] = None
        self.tracked_vehicles: Dict[str, Dict[str, Any]] = {}
        self.persisted_tracks: Set[str] = set()

        # Database session engine
        self._db_engine = None
        if self.enable_db_persist:
            try:
                self._db_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            except Exception as e:
                logger.warning(f"Could not connect DB engine for {camera_id}: {e}")
                self._db_engine = None

    def log(self, tag: str, **kwargs) -> None:
        """Structured perception logger."""
        if not self.enable_logging:
            return
        details = " ".join(f"{k}={v}" for k, v in kwargs.items())
        print(f"[{tag}] {details}")

    def _persist_track_if_ready(self, track_id_str: str, force: bool = False) -> None:
        """Persist a track observation if it reached finalization threshold and hasn't been persisted yet."""
        if not self.enable_db_persist or self._db_engine is None or track_id_str in self.persisted_tracks:
            return

        trk_info = self.tracked_vehicles.get(track_id_str)
        if not trk_info:
            return

        # Finalization condition: vehicle has been tracked for >= 5 frames OR forced finalization on exit
        if force or trk_info.get("frames", 0) >= 5 or trk_info.get("is_moving", False):
            fused = self.fusion.fuse_track(
                camera_id=self.camera_id,
                track_id=track_id_str,
                vehicle_type=trk_info.get("type", "car"),
                vehicle_colour=trk_info.get("color", "white"),
            )

            # Extract track-level appearance embedding if Re-ID is enabled
            appearance_embedding = None
            if settings.APPEARANCE_REID_ENABLED and "crops" in trk_info and trk_info["crops"]:
                try:
                    from app.modules.appearance import get_appearance_extractor
                    extractor = get_appearance_extractor()
                    appearance_embedding = extractor.extract_track_embedding(trk_info["crops"])
                except Exception as e:
                    logger.debug(f"Track embedding extraction failed for {track_id_str}: {e}")
                    appearance_embedding = None
                finally:
                    trk_info["crops"].clear()

            try:
                with Session(self._db_engine) as session:
                    obs = persist_fused_observation(
                        session=session,
                        camera_id_str=self.camera_id,
                        track_id=track_id_str,
                        captured_at=trk_info.get("first_seen", datetime.now(timezone.utc).isoformat()),
                        fused_plate_text=fused.get("fused_plate_text", "NOT READ"),
                        fused_confidence=fused.get("fused_confidence"),
                        vehicle_type=fused.get("vehicle_type", "car"),
                        vehicle_colour=fused.get("vehicle_colour", "white"),
                        ocr_reads=fused.get("reads_history", []),
                        appearance_embedding=appearance_embedding,
                    )
                    if obs:
                        self.persisted_tracks.add(track_id_str)
                        try:
                            from app.modules.identity import match_new_observation
                            match_new_observation(session, obs)
                        except Exception as fuse_err:
                            logger.debug(f"Online identity fusion error for {track_id_str}: {fuse_err}")
            except Exception as e:
                logger.warning(f"[DB ERROR] Error persisting track {track_id_str}: {e}")

    def process_frame(
        self,
        frame: np.ndarray,
        frame_id: int,
        timestamp: Optional[str] = None,
        simulate_ocr_failure: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Process one video frame through YOLO -> ByteTrack -> Plate Localizer -> PaddleOCR -> Fusion -> DB."""
        current_time_str = timestamp or datetime.now(timezone.utc).strftime("%I:%M:%S %p")
        frame_observations: List[Dict[str, Any]] = []
        top_active_vehicle: Optional[Dict[str, Any]] = None
        top_motion_score = -1.0
        seen_tracks_in_frame: Set[str] = set()

        h, w = frame.shape[:2]

        # 1. YOLO Detection with ByteTrack Tracking (persist=True, tracker="bytetrack.yaml")
        try:
            results = self.model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[2, 3, 5, 7],
                conf=self.confidence,
                verbose=False,
            )[0]
        except Exception as e:
            logger.error(f"YOLO/ByteTrack inference failure on {self.camera_id}: {e}")
            return [], None

        boxes = results.boxes
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls_id = int(box.cls[0]) if box.cls is not None else 2
                if cls_id not in VEHICLE_CLASS_MAP:
                    continue

                vtype = VEHICLE_CLASS_MAP.get(cls_id, "car")
                conf = float(box.conf[0]) if box.conf is not None else 0.85
                bbox_coords = box.xyxy[0].tolist()
                x1, y1, x2, y2 = [int(v) for v in bbox_coords]

                # ByteTrack track ID
                track_int = int(box.id[0]) if box.id is not None else 1
                track_id_str = f"TRK-{track_int:03d}"
                obs_id_str = f"TRACE-{self.camera_id.upper()}-{track_int:02d}"
                seen_tracks_in_frame.add(track_id_str)

                # Log YOLO detection
                self.log(
                    "YOLO",
                    camera=self.camera_id,
                    frame=frame_id,
                    vehicle_class=vtype,
                    confidence=round(conf, 2),
                    bbox=f"({x1},{y1},{x2},{y2})",
                )

                # Log ByteTrack tracking
                self.log(
                    "TRACK",
                    camera=self.camera_id,
                    frame=frame_id,
                    track_id=track_id_str,
                    vehicle_class=vtype,
                )

                # Crop vehicle for color extraction
                veh_crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
                color = _detect_crop_color(veh_crop)

                # Update motion tracking
                cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                if track_id_str in self.tracked_vehicles:
                    trk_info = self.tracked_vehicles[track_id_str]
                    trk_info["cx"] = cx
                    trk_info["cy"] = cy
                    trk_info["frames"] += 1
                    trk_info["last_frame"] = frame_id
                    disp = math.hypot(cx - trk_info["start_cx"], cy - trk_info["start_cy"])
                    trk_info["displacement"] = disp
                    is_moving = disp > 12.0
                    trk_info["is_moving"] = is_moving
                else:
                    trk_info = {
                        "start_cx": cx,
                        "start_cy": cy,
                        "cx": cx,
                        "cy": cy,
                        "frames": 1,
                        "last_frame": frame_id,
                        "displacement": 0.0,
                        "color": color,
                        "type": vtype,
                        "first_seen": current_time_str,
                        "is_moving": False,
                        "crops": [],
                    }
                    self.tracked_vehicles[track_id_str] = trk_info
                    disp = 0.0
                    is_moving = False

                # Collect high-quality vehicle crops for track appearance embedding
                if "crops" not in trk_info:
                    trk_info["crops"] = []
                if len(trk_info["crops"]) < settings.APPEARANCE_MAX_TRACK_SAMPLES:
                    if veh_crop is not None and veh_crop.size > 0:
                        if veh_crop.shape[0] >= settings.APPEARANCE_MIN_CROP_SIZE and veh_crop.shape[1] >= settings.APPEARANCE_MIN_CROP_SIZE:
                            trk_info["crops"].append(veh_crop.copy())

                # 2. License Plate Localization & PaddleOCR
                plate_raw_text = ""
                plate_conf = 0.0
                plate_bbox = None

                if self.enable_ocr:
                    try:
                        if simulate_ocr_failure:
                            raise RuntimeError("Simulated OCR exception for robustness testing")

                        plate_crop = extract_plate_crop(veh_crop)
                        plate_bbox = [x1, int(y1 + 0.6 * (y2 - y1)), x2, y2]
                        
                        self.log(
                            "PLATE",
                            camera=self.camera_id,
                            frame=frame_id,
                            track_id=track_id_str,
                            plate_bbox=f"({plate_bbox[0]},{plate_bbox[1]},{plate_bbox[2]},{plate_bbox[3]})",
                        )

                        ocr_results = read_plate_image(plate_crop, min_confidence=0.25)
                        if ocr_results:
                            best_ocr = max(ocr_results, key=lambda x: x["confidence"])
                            plate_raw_text = best_ocr["raw_text"]
                            plate_conf = best_ocr["confidence"]
                            norm_text = best_ocr["normalized_text"]

                            self.log(
                                "OCR",
                                camera=self.camera_id,
                                frame=frame_id,
                                track_id=track_id_str,
                                raw_text=plate_raw_text,
                                normalized_text=norm_text,
                                ocr_confidence=round(plate_conf, 2),
                            )

                            self.fusion.add_ocr_read(
                                camera_id=self.camera_id,
                                track_id=track_id_str,
                                frame_id=frame_id,
                                raw_text=plate_raw_text,
                                confidence=plate_conf,
                                timestamp=current_time_str,
                            )
                        else:
                            self.log(
                                "OCR WARNING",
                                camera=self.camera_id,
                                frame=frame_id,
                                track_id=track_id_str,
                                status="unreadable",
                            )

                    except Exception as ocr_err:
                        self.log(
                            "OCR WARNING",
                            camera=self.camera_id,
                            frame=frame_id,
                            track_id=track_id_str,
                            status=f"exception: {ocr_err}",
                        )

                # 3. Temporal OCR Fusion query
                fused = self.fusion.fuse_track(
                    camera_id=self.camera_id,
                    track_id=track_id_str,
                    vehicle_type=vtype,
                    vehicle_colour=color,
                )

                if fused["ocr_samples_count"] > 0:
                    self.log(
                        "FUSION",
                        camera=self.camera_id,
                        track_id=track_id_str,
                        fused_text=fused["fused_plate_text"],
                        fused_confidence=fused["fused_confidence"],
                        samples=fused["ocr_samples_count"],
                    )

                obs_data = {
                    "camera_id": self.camera_id,
                    "observation_id": obs_id_str,
                    "track_id": track_id_str,
                    "vehicle_type": vtype,
                    "vehicle_colour": color,
                    "plate": fused["fused_plate_text"],
                    "ocr_confidence": fused["fused_confidence"],
                    "timestamp": current_time_str,
                    "is_moving": is_moving,
                    "bbox": [x1, y1, x2, y2],
                }
                frame_observations.append(obs_data)

                # 4. Check track persistence lifecycle
                self._persist_track_if_ready(track_id_str)

                # Motion score prioritizing passing cars for active display
                motion_score = (1000.0 if is_moving else 0.0) + disp + (conf * 10)
                if motion_score > top_motion_score:
                    top_motion_score = motion_score
                    top_active_vehicle = obs_data

        # Finalize stale tracks that have exited FOV
        stale_tracks = [
            tid for tid, info in self.tracked_vehicles.items()
            if tid not in seen_tracks_in_frame and (frame_id - info.get("last_frame", 0)) > 15
        ]
        for tid in stale_tracks:
            self._persist_track_if_ready(tid, force=True)

        if top_active_vehicle:
            self.current_observation = top_active_vehicle

        return frame_observations, self.current_observation

    def finalize_all_tracks(self) -> None:
        """Force finalize and persist any remaining active tracks (e.g. on stream completion)."""
        for tid in list(self.tracked_vehicles.keys()):
            self._persist_track_if_ready(tid, force=True)
