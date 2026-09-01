"""
Vehicle schemas — Pydantic models for trajectory and identity evidence responses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import uuid

from pydantic import BaseModel


class EvidenceBreakdown(BaseModel):
    """Explainability evidence for a single identity score (NFR-07)."""
    plate_similarity: float
    """Normalized Levenshtein similarity between the two fused plate texts [0–1]."""
    ocr_confidence_component: float
    """Reliability-weighted average OCR confidence of both observations [0–1]."""
    attribute_match: float
    """Average of type_match and colour_match booleans expressed as [0, 0.5, 1]."""
    camera_reliability_weight: float
    """Average day/night OCR reliability across the two cameras [0–1]."""


class ObservationInTrajectory(BaseModel):
    observation_id: uuid.UUID
    camera_id: uuid.UUID
    camera_name: Optional[str] = None
    captured_at: datetime
    fused_plate_text: str
    fused_confidence: float
    vehicle_type: str
    vehicle_colour: str

    # Identity fields
    identity_score: Optional[float] = None
    """Composite match score from the M3 identity scoring formula [0–1]."""
    match_confidence_label: Optional[str] = None
    """One of: 'confirmed' (≥0.70), 'candidate' (0.40–0.70), 'no_match' (<0.40)."""
    is_impossible_journey: Optional[bool] = None

    # Evidence breakdown (NFR-07 explainability)
    evidence: Optional[EvidenceBreakdown] = None

    # Geospatial (may be None until M4 wires DB locations)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}


class TrajectoryResponse(BaseModel):
    plate: str
    observations: List[ObservationInTrajectory]
