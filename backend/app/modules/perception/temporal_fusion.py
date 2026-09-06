"""Layer 1 — Perception Module: Track-level Temporal OCR Fusion Engine."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.perception.normalization import normalize_plate_text

logger = logging.getLogger("trace.perception.temporal_fusion")


@dataclass
class OCRReadRecord:
    """Individual per-frame OCR detection record (maps to TRACE ocr_reads schema)."""
    frame_id: int
    timestamp: str
    camera_id: str
    track_id: str | int
    raw_plate_text: str
    normalized_plate_text: str
    confidence: float
    bbox: Optional[List[Any]] = None


class TemporalOCRFusion:
    """Aggregates and fuses multi-frame OCR reads for tracked vehicles."""

    def __init__(self, min_samples_for_lock: int = 2):
        self.min_samples_for_lock = min_samples_for_lock
        # Map: track_key (e.g. "c020:TRK-001" or "TRK-001") -> List[OCRReadRecord]
        self._track_reads: Dict[str, List[OCRReadRecord]] = defaultdict(list)

    def add_ocr_read(
        self,
        camera_id: str,
        track_id: str | int,
        frame_id: int,
        raw_text: str,
        confidence: float,
        timestamp: Optional[str] = None,
        bbox: Optional[List[Any]] = None,
    ) -> Optional[OCRReadRecord]:
        """Record a single frame OCR observation for a vehicle track."""
        norm_text = normalize_plate_text(raw_text)
        if not norm_text or confidence <= 0.0:
            return None

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        record = OCRReadRecord(
            frame_id=frame_id,
            timestamp=ts,
            camera_id=camera_id,
            track_id=str(track_id),
            raw_plate_text=raw_text,
            normalized_plate_text=norm_text,
            confidence=round(float(confidence), 4),
            bbox=bbox,
        )

        track_key = f"{camera_id}:{track_id}"
        self._track_reads[track_key].append(record)
        return record

    def fuse_track(
        self,
        camera_id: str,
        track_id: str | int,
        vehicle_type: str = "car",
        vehicle_colour: str = "white",
    ) -> Dict[str, Any]:
        """Compute the temporally fused plate reading for a given track.
        
        Returns a dictionary formatted for TRACE vehicle_observations schema.
        """
        track_key = f"{camera_id}:{track_id}"
        reads = self._track_reads.get(track_key, [])

        if not reads:
            return {
                "camera_id": camera_id,
                "track_id": str(track_id),
                "fused_plate_text": "NOT READ",
                "fused_confidence": None,
                "vehicle_type": vehicle_type,
                "vehicle_colour": vehicle_colour,
                "ocr_samples_count": 0,
                "reads_history": [],
            }

        # Weighted temporal voting: aggregate confidence scores per unique candidate text
        candidate_scores: Dict[str, float] = defaultdict(float)
        candidate_counts: Dict[str, int] = defaultdict(int)
        candidate_max_conf: Dict[str, float] = defaultdict(float)

        for r in reads:
            text = r.normalized_plate_text
            # Exponentially weight higher confidence reads
            weight = r.confidence ** 1.5
            candidate_scores[text] += weight
            candidate_counts[text] += 1
            if r.confidence > candidate_max_conf[text]:
                candidate_max_conf[text] = r.confidence

        # Select candidate with highest cumulative weighted score
        best_candidate = max(candidate_scores.keys(), key=lambda t: (candidate_scores[t], candidate_counts[t]))
        
        # Calculate fused confidence: base max confidence + small bonus for multi-frame agreement (capped at 0.99)
        base_conf = candidate_max_conf[best_candidate]
        agreement_ratio = candidate_counts[best_candidate] / len(reads)
        sample_bonus = min(0.08, 0.02 * (candidate_counts[best_candidate] - 1))
        fused_conf = min(0.99, round(base_conf * (0.92 + 0.08 * agreement_ratio) + sample_bonus, 4))

        first_seen = reads[0].timestamp
        last_seen = reads[-1].timestamp

        return {
            "camera_id": camera_id,
            "track_id": str(track_id),
            "fused_plate_text": best_candidate,
            "fused_confidence": fused_conf,
            "vehicle_type": vehicle_type,
            "vehicle_colour": vehicle_colour,
            "ocr_samples_count": len(reads),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "reads_history": [
                {
                    "frame_id": r.frame_id,
                    "raw_text": r.raw_plate_text,
                    "normalized_text": r.normalized_plate_text,
                    "confidence": r.confidence,
                    "timestamp": r.timestamp,
                }
                for r in reads
            ],
        }

    def clear_track(self, camera_id: str, track_id: str | int) -> None:
        """Prune track history when vehicle leaves the scene."""
        track_key = f"{camera_id}:{track_id}"
        self._track_reads.pop(track_key, None)

