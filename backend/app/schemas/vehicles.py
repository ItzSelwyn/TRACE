"""
Vehicle schemas — Pydantic models for trajectory and identity evidence responses.
M3: added EvidenceBreakdown and identity fields.
M4: added anomaly fields (implied_speed_kmph, anomaly_type) and anomaly_flags on response.
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

    # Identity fields (M3)
    identity_score: Optional[float] = None
    """Composite match score from the M3 identity scoring formula [0–1]."""
    match_confidence_label: Optional[str] = None
    """One of: 'confirmed' (≥0.70), 'candidate' (0.40–0.70), 'no_match' (<0.40)."""

    # Evidence breakdown (M3 — NFR-07 explainability)
    evidence: Optional[EvidenceBreakdown] = None

    # Anomaly fields (M4 — FR-STR-04, FR-PRD-02)
    is_impossible_journey: Optional[bool] = None
    """True when implied travel speed exceeds speed_limit × 1.5 (FR-STR-04)."""
    implied_speed_kmph: Optional[float] = None
    """Computed travel speed between this and the previous observation."""
    anomaly_type: Optional[str] = None
    """One of: 'impossible_journey' | 'duplicate_plate' | 'camera_inconsistency', or None."""

    # Geospatial (M4 wires camera lat/lon from seed data)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}


class TrajectoryResponse(BaseModel):
    plate: str
    observations: List[ObservationInTrajectory]
    # M4 additions
    anomaly_flags: List[str] = []
    """Distinct anomaly types present in this trajectory."""
    total_anomalies: int = 0
    """Total count of flagged anomaly events."""
