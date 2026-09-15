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
from app.modules.appearance.preprocessing import score_crop_quality
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
    """Classify dominant vehicle color using robust RGB/HSV analysis on vehicle core crop.

    Accurately identifies: RED, ORANGE, YELLOW, GREEN, BLUE, BLACK, WHITE, SILVER.
    Filters out sky/windshield reflection, tinted glass, asphalt shadows, and specular glare.
    """
    if crop is None or crop.size == 0 or crop.shape[0] < 6 or crop.shape[1] < 6:
        return "SILVER"
    try:
        h, w = crop.shape[:2]

        # Target the vehicle body: 35% - 78% height (bypasses windshield sky reflection & road/wheels)
        # and 15% - 85% width (bypasses side backgrounds/curbs)
        b_y1, b_y2 = int(h * 0.35), int(h * 0.78)
        b_x1, b_x2 = int(w * 0.15), int(w * 0.85)
        body = crop[b_y1:b_y2, b_x1:b_x2]
        if body.size == 0 or body.shape[0] < 4 or body.shape[1] < 4:
            body = crop

        bgr = body.astype(float)
        max_c = np.max(bgr, axis=2)
        min_c = np.min(bgr, axis=2)
        delta_rgb = max_c - min_c

        hsv = cv2.cvtColor(body, cv2.COLOR_BGR2HSV)
        H = hsv[:, :, 0]
        S = hsv[:, :, 1]
        V = hsv[:, :, 2]

        # Valid non-black mask (exclude deep shadow crevices V < 35)
        valid_mask = (V >= 35)
        if np.sum(valid_mask) < 20:
            valid_mask = np.ones_like(V, dtype=bool)

        H_v = H[valid_mask]
        S_v = S[valid_mask]
        V_v = V[valid_mask]
        delta_v = delta_rgb[valid_mask]

        med_delta = float(np.median(delta_v))
        med_s = float(np.median(S_v))
        med_v = float(np.median(V))  # overall median of body

        # 1. Check BLACK first: overall body median V < 75
        if med_v < 75:
            chroma_dark = (S_v >= 90) & (delta_v >= 45) & (V_v >= 45)
            if np.sum(chroma_dark) / max(1, len(S_v)) < 0.35:
                return "BLACK"

        # 2. Chromatic detection:
        # A true colored car has high saturation AND significant channel difference (delta_rgb).
        # Sky reflections on silver cars have low delta_rgb (< 28) even if Hue is in the blue range.
        # Therefore, true chromatic pixels must satisfy S >= 60 AND delta_rgb >= 30 AND V >= 45.
        chroma_pixels = (S_v >= 60) & (delta_v >= 30) & (V_v >= 45)
        chroma_ratio = float(np.sum(chroma_pixels)) / max(1, len(S_v))

        if chroma_ratio >= 0.28 or (med_delta >= 38 and chroma_ratio >= 0.18):
            h_chroma = H_v[chroma_pixels]
            red_cnt = int(np.sum((h_chroma <= 9) | (h_chroma >= 165)))
            orange_cnt = int(np.sum((h_chroma >= 10) & (h_chroma <= 24)))
            yellow_cnt = int(np.sum((h_chroma >= 25) & (h_chroma <= 35)))
            green_cnt = int(np.sum((h_chroma >= 36) & (h_chroma <= 85)))
            # Blue range: 86 to 140
            blue_cnt = int(np.sum((h_chroma >= 86) & (h_chroma <= 140)))

            counts = {
                "RED": red_cnt,
                "ORANGE": orange_cnt,
                "YELLOW": yellow_cnt,
                "GREEN": green_cnt,
                "BLUE": blue_cnt,
            }
            best_col, best_n = max(counts.items(), key=lambda x: x[1])
            # The best color must represent at least 38% of the chromatic pixels
            if best_n > 0 and (best_n / max(1, len(h_chroma))) >= 0.38:
                return best_col

        # 3. Achromatic classification: WHITE vs SILVER / GREY
        # Compute high brightness ratio among paint pixels
        n_mid = int(np.sum((V >= 90) & (V < 200)))
        n_high = int(np.sum(V >= 200))
        total_bright = n_mid + n_high
        ratio_high = (n_high / total_bright) if total_bright > 0 else 0.0

        # White vehicles have high brightness paint (ratio_high >= 0.55 or med_v >= 200)
        if ratio_high >= 0.55 or med_v >= 200:
            return "WHITE"
        elif med_v < 85:
            return "BLACK"
        else:
            return "SILVER"
    except Exception as exc:
        logger.warning(f"Error in _detect_crop_color: {exc}")
        return "SILVER"


class PerceptionPipeline:
    """End-to-end perception pipeline for a single camera stream with PostgreSQL persistence."""

    def __init__(
        self,
        camera_id: str,
        yolo_model_path: str = "yolov8n.pt",
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
            Path(yolo_model_path),
            root / "backend" / yolo_model_path,
            root / "backend" / "yolov8n.pt",
            root / "backend" / "yolo8n.pt",
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

            # Extract appearance embedding
            appearance_embedding = None
            emb_status = "pending"
            emb_reason = None
            if settings.APPEARANCE_REID_ENABLED:
                try:
                    from app.modules.appearance import get_appearance_extractor
                    extractor = get_appearance_extractor()
                    candidate = trk_info.get("best_crop")
                    if candidate is not None:
                        appearance_embedding, emb_reason = extractor.extract_with_reason(
                            candidate, min_size=settings.APPEARANCE_MIN_CROP_SIZE
                        )
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
                        embedding_status=emb_status,
                        embedding_failure_reason=emb_reason,
                        embedding_attempts=1,
                    )
                    if obs:
                        self.persisted_tracks.add(track_id_str)
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
                        "best_crop": veh_crop.copy() if (veh_crop is not None and veh_crop.size > 0 and veh_crop.shape[0] >= 24 and veh_crop.shape[1] >= 24) else None,
                        "best_crop_score": 0.0,
                    }
                    self.tracked_vehicles[track_id_str] = trk_info
                    disp = 0.0
                    is_moving = False

                if veh_crop is not None and veh_crop.size > 0:
                    crop_score = score_crop_quality(crop=veh_crop, bbox=[x1, y1, x2, y2], frame_shape=(h, w), conf=conf)
                    if crop_score > trk_info.get("best_crop_score", 0.0) or trk_info.get("best_crop") is None:
                        if veh_crop.shape[0] >= 24 and veh_crop.shape[1] >= 24:
                            trk_info["best_crop"] = veh_crop.copy()
                            trk_info["best_crop_score"] = crop_score

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
