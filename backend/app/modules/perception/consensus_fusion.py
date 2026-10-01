"""Layer 1 — Perception Module: Sequence-Aligned Multi-Frame OCR Consensus Fusion."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.modules.perception.indian_format import (
    FormatCorrectionResult,
    clean_alphanumeric,
    correct_indian_plate_format,
)

logger = logging.getLogger("trace.perception.consensus_fusion")


@dataclass
class OCRTrackCandidate:
    """Individual per-frame / per-variant OCR candidate observation."""
    frame_id: int
    raw_text: str
    normalized_text: str
    confidence: float
    crop_quality_score: float = 0.5
    variant: str = "ORIGINAL"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    char_scores: Optional[List[float]] = None


def needleman_wunsch_align(seq_a: str, seq_b: str, match_score: int = 2, mismatch_penalty: int = -1, gap_penalty: int = -2) -> Tuple[str, str]:
    """Perform global sequence alignment between two character strings."""
    m, n = len(seq_a), len(seq_b)
    if m == 0:
        return "-" * n, seq_b
    if n == 0:
        return seq_a, "-" * m

    score_matrix = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        score_matrix[i][0] = i * gap_penalty
    for j in range(n + 1):
        score_matrix[0][j] = j * gap_penalty

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match = score_matrix[i - 1][j - 1] + (match_score if seq_a[i - 1] == seq_b[j - 1] else mismatch_penalty)
            delete = score_matrix[i - 1][j] + gap_penalty
            insert = score_matrix[i][j - 1] + gap_penalty
            score_matrix[i][j] = max(match, delete, insert)

    # Traceback
    aligned_a: List[str] = []
    aligned_b: List[str] = []
    i, j = m, n

    while i > 0 or j > 0:
        if i > 0 and j > 0 and (
            score_matrix[i][j] == score_matrix[i - 1][j - 1] + (match_score if seq_a[i - 1] == seq_b[j - 1] else mismatch_penalty)
        ):
            aligned_a.append(seq_a[i - 1])
            aligned_b.append(seq_b[j - 1])
            i -= 1
            j -= 1
        elif i > 0 and (score_matrix[i][j] == score_matrix[i - 1][j] + gap_penalty):
            aligned_a.append(seq_a[i - 1])
            aligned_b.append("-")
            i -= 1
        else:
            aligned_a.append("-")
            aligned_b.append(seq_b[j - 1])
            j -= 1

    return "".join(reversed(aligned_a)), "".join(reversed(aligned_b))


class TrackTemporalConsensus:
    """Manages multi-frame OCR candidates for a vehicle track and computes sequence-aligned consensus."""

    def __init__(self, track_id: str, camera_id: str):
        self.track_id = str(track_id)
        self.camera_id = camera_id
        self.candidates: List[OCRTrackCandidate] = []
        self.best_raw_text: str = ""
        self.best_raw_confidence: float = 0.0
        self.best_crop_quality: float = 0.0

    def add_candidate(
        self,
        frame_id: int,
        raw_text: str,
        normalized_text: str,
        confidence: float,
        crop_quality_score: float = 0.5,
        variant: str = "ORIGINAL",
        char_scores: Optional[List[float]] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Register a new candidate reading from any frame or preprocessing variant."""
        clean_raw = str(raw_text or "").strip().upper()
        clean_norm = str(normalized_text or "").strip().upper()
        if not clean_norm or confidence <= 0.0:
            return

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        cand = OCRTrackCandidate(
            frame_id=frame_id,
            raw_text=clean_raw,
            normalized_text=clean_norm,
            confidence=round(float(confidence), 4),
            crop_quality_score=round(float(crop_quality_score), 4),
            variant=variant,
            timestamp=ts,
            char_scores=char_scores,
        )
        self.candidates.append(cand)

        if cand.confidence > self.best_raw_confidence:
            self.best_raw_confidence = cand.confidence
            self.best_raw_text = cand.raw_text

        if cand.crop_quality_score > self.best_crop_quality:
            self.best_crop_quality = cand.crop_quality_score

    def compute_consensus(self) -> Dict[str, Any]:
        """Align candidates, perform confidence-weighted character voting, and apply format correction."""
        if not self.candidates:
            return {
                "raw_ocr_text": "",
                "corrected_plate_text": "NOT READ",
                "display_plate": "NOT READ",
                "ocr_confidence": None,
                "correction_confidence": None,
                "plate_status": "NOT_READ",
                "inferred_positions": [],
                "is_synthetic": False,
                "candidates_count": 0,
            }

        # 1. Select anchor candidate: highest composite of confidence & crop quality
        anchor = max(
            self.candidates,
            key=lambda c: (c.confidence ** 1.5) * (0.6 + 0.4 * c.crop_quality_score),
        )

        anchor_str = anchor.normalized_text
        if len(self.candidates) == 1 or len(anchor_str) == 0:
            # Single candidate fallback
            fmt_res = correct_indian_plate_format(anchor_str, raw_confidence=anchor.confidence)
            display = fmt_res.corrected_text if fmt_res.plate_status in ["READ", "INFERRED", "PARTIAL"] else "NOT READ"
            return {
                "raw_ocr_text": anchor.raw_text,
                "corrected_plate_text": fmt_res.corrected_text,
                "display_plate": display,
                "ocr_confidence": anchor.confidence,
                "correction_confidence": fmt_res.correction_confidence,
                "plate_status": fmt_res.plate_status,
                "inferred_positions": fmt_res.inferred_positions,
                "is_synthetic": False,
                "candidates_count": 1,
            }

        # 2. Pairwise sequence alignment against anchor to establish column correspondence
        # aligned_columns maps column_idx -> Dict[char, weighted_score]
        column_votes: List[Dict[str, float]] = []
        anchor_len = len(anchor_str)
        for _ in range(anchor_len):
            column_votes.append(defaultdict(float))

        # Anchor votes for itself
        anchor_weight = (anchor.confidence ** 1.5) * (0.6 + 0.4 * anchor.crop_quality_score)
        for idx, ch in enumerate(anchor_str):
            column_votes[idx][ch] += anchor_weight

        for cand in self.candidates:
            if cand is anchor:
                continue
            cand_str = cand.normalized_text
            weight = (cand.confidence ** 1.5) * (0.6 + 0.4 * cand.crop_quality_score)

            if len(cand_str) == anchor_len:
                # Direct index mapping when lengths match exactly
                for idx, ch in enumerate(cand_str):
                    column_votes[idx][ch] += weight
            else:
                # Sequence-aligned mapping
                aligned_anch, aligned_cand = needleman_wunsch_align(anchor_str, cand_str)
                anch_idx = 0
                for a_ch, c_ch in zip(aligned_anch, aligned_cand):
                    if a_ch != "-":
                        if c_ch != "-" and anch_idx < anchor_len:
                            column_votes[anch_idx][c_ch] += weight
                        anch_idx += 1

        # 3. Resolve consensus characters per column
        consensus_chars: List[str] = []
        col_confidences: List[float] = []

        for votes in column_votes:
            if not votes:
                continue
            best_char = max(votes.keys(), key=lambda c: votes[c])
            total_vote = sum(votes.values())
            ratio = votes[best_char] / max(1e-4, total_vote)
            consensus_chars.append(best_char)
            col_confidences.append(ratio)

        consensus_str = "".join(consensus_chars)

        # Base OCR confidence from top candidate + multi-frame agreement bonus
        base_conf = anchor.confidence
        agreement_avg = float(sum(col_confidences) / max(1, len(col_confidences)))
        sample_bonus = min(0.08, 0.015 * (len(self.candidates) - 1))
        fused_conf = round(float(np.clip(base_conf * 0.90 + agreement_avg * 0.10 + sample_bonus, 0.20, 0.99)), 4)

        # 4. Indian registration-format correction
        fmt_res: FormatCorrectionResult = correct_indian_plate_format(
            consensus_str,
            raw_confidence=fused_conf,
            min_confidence_for_read=0.80,
        )

        display = fmt_res.corrected_text if fmt_res.plate_status in ["READ", "INFERRED", "PARTIAL"] else "NOT READ"

        return {
            "raw_ocr_text": self.best_raw_text or anchor.raw_text,
            "corrected_plate_text": fmt_res.corrected_text,
            "display_plate": display,
            "ocr_confidence": fused_conf,
            "correction_confidence": fmt_res.correction_confidence,
            "plate_status": fmt_res.plate_status,
            "inferred_positions": fmt_res.inferred_positions,
            "is_synthetic": False,
            "candidates_count": len(self.candidates),
        }
