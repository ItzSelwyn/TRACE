"""Layer 1 — Perception Module: Track-level Temporal OCR Fusion Engine with Sequence-Aligned Consensus."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.perception.consensus_fusion import TrackTemporalConsensus
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
    crop_quality_score: float = 0.5
    variant: str = "ORIGINAL"


class TemporalOCRFusion:
    """Aggregates and fuses multi-frame OCR reads for tracked vehicles using sequence alignment."""

    def __init__(self, min_samples_for_lock: int = 2):
        self.min_samples_for_lock = min_samples_for_lock
        # Map: track_key (e.g. "c020:TRK-001") -> List[OCRReadRecord]
        self._track_reads: Dict[str, List[OCRReadRecord]] = defaultdict(list)
        # Map: track_key -> TrackTemporalConsensus
        self._track_consensus: Dict[str, TrackTemporalConsensus] = {}

    def add_ocr_read(
        self,
        camera_id: str,
        track_id: str | int,
        frame_id: int,
        raw_text: str,
        confidence: float,
        timestamp: Optional[str] = None,
        bbox: Optional[List[Any]] = None,
        crop_quality_score: float = 0.5,
        variant: str = "ORIGINAL",
        char_scores: Optional[List[float]] = None,
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
            crop_quality_score=round(float(crop_quality_score), 4),
            variant=variant,
        )

        track_key = f"{camera_id}:{track_id}"
        self._track_reads[track_key].append(record)

        if track_key not in self._track_consensus:
            self._track_consensus[track_key] = TrackTemporalConsensus(str(track_id), camera_id)

        self._track_consensus[track_key].add_candidate(
            frame_id=frame_id,
            raw_text=raw_text,
            normalized_text=norm_text,
            confidence=confidence,
            crop_quality_score=crop_quality_score,
            variant=variant,
            char_scores=char_scores,
            timestamp=ts,
        )

        return record

    def fuse_track(
        self,
        camera_id: str,
        track_id: str | int,
        vehicle_type: str = "car",
        vehicle_colour: str = "white",
    ) -> Dict[str, Any]:
        """Compute sequence-aligned temporally fused plate reading for a given track."""
        track_key = f"{camera_id}:{track_id}"
        reads = self._track_reads.get(track_key, [])
        consensus_mgr = self._track_consensus.get(track_key)

        if not reads or consensus_mgr is None:
            return {
                "camera_id": camera_id,
                "track_id": str(track_id),
                "fused_plate_text": "NOT READ",
                "fused_confidence": None,
                "raw_ocr_text": "",
                "corrected_plate_text": "NOT READ",
                "display_plate": "NOT READ",
                "ocr_confidence": None,
                "correction_confidence": None,
                "plate_status": "NOT_READ",
                "inferred_positions": [],
                "is_synthetic": False,
                "vehicle_type": vehicle_type,
                "vehicle_colour": vehicle_colour,
                "ocr_samples_count": 0,
                "reads_history": [],
            }

        res = consensus_mgr.compute_consensus()
        status = res.get("plate_status", "NOT_READ")
        corr_text = res.get("corrected_plate_text", "NOT READ")
        conf = res.get("ocr_confidence")

        # Trusted genuine plate for DB persistence and re-id is only populated if READ or INFERRED
        trusted_plate = corr_text if status in ["READ", "INFERRED"] else "NOT READ"
        trusted_conf = conf if trusted_plate != "NOT READ" else None

        first_seen = reads[0].timestamp
        last_seen = reads[-1].timestamp

        return {
            "camera_id": camera_id,
            "track_id": str(track_id),
            "fused_plate_text": trusted_plate,
            "fused_confidence": trusted_conf,
            "raw_ocr_text": res.get("raw_ocr_text", ""),
            "corrected_plate_text": corr_text,
            "display_plate": res.get("display_plate", trusted_plate),
            "ocr_confidence": conf,
            "correction_confidence": res.get("correction_confidence"),
            "plate_status": status,
            "inferred_positions": res.get("inferred_positions", []),
            "is_synthetic": False,
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
                    "crop_quality_score": r.crop_quality_score,
                    "variant": r.variant,
                }
                for r in reads
            ],
        }

    def clear_track(self, camera_id: str, track_id: str | int) -> None:
        """Prune track history when vehicle leaves the scene."""
        track_key = f"{camera_id}:{track_id}"
        self._track_reads.pop(track_key, None)
        self._track_consensus.pop(track_key, None)

    def clear_all(self) -> None:
        """Prune all tracks on dataset reset or camera restart."""
        self._track_reads.clear()
        self._track_consensus.clear()
