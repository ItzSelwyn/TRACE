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
    # Plate evidence (None when plate unavailable — CityFlowV2 mode)
    plate_similarity: Optional[float] = None
    """Normalized Levenshtein similarity between the two fused plate texts [0–1]."""
    ocr_confidence_component: Optional[float] = None
    """Reliability-weighted average OCR confidence of both observations [0–1]."""
    attribute_match: Optional[float] = None
    """Average of type and colour soft scores [0–1]."""
    camera_reliability_weight: Optional[float] = None
    """Average day/night OCR reliability across the two cameras [0–1]."""
    # New multi-modal evidence fields
    appearance_similarity: Optional[float] = None
    """Cosine/re-ID appearance similarity [0–1], or None if pipeline not available."""
    temporal_score: Optional[float] = None
    """Temporal plausibility: 1.0=reachable, 0.5=unknown, 0.0=impossible [0–1]."""
    camera_transition_score: Optional[float] = None
    """Camera-to-camera transition score: 1.0=direct edge, 0.7=multi-hop, 0.3=unknown."""
    mode: Optional[str] = None
    """Scoring mode: 'ANPR' or 'CITYFLOW'."""


class ObservationInTrajectory(BaseModel):
    observation_id: uuid.UUID
    camera_id: uuid.UUID
    camera_name: Optional[str] = None
    captured_at: datetime
    fused_plate_text: Optional[str] = ""
    fused_confidence: float
    vehicle_type: str
    vehicle_colour: str
    track_id: Optional[str] = None
    canonical_vehicle_id: Optional[uuid.UUID] = None

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
    plate: Optional[str] = None
    vehicle_id: Optional[str] = None
    search_query: Optional[str] = None
    identifier_type: Optional[str] = None
    observations: List[ObservationInTrajectory]
    # M4 additions
    anomaly_flags: List[str] = []
    """Distinct anomaly types present in this trajectory."""
    total_anomalies: int = 0
    """Total count of flagged anomaly events."""


class VehicleSearchResult(BaseModel):
    """Result item for multi-identifier vehicle search."""
    identifier: str
    identifier_type: str  # 'canonical_id' | 'track_id' | 'observation_id' | 'plate'
    canonical_vehicle_id: Optional[uuid.UUID] = None
    vehicle_type: str
    vehicle_colour: str
    latest_camera: Optional[str] = None
    latest_timestamp: Optional[datetime] = None
    has_plate: bool = False
    observation_count: int = 1

    model_config = {"from_attributes": True}


class VehicleSearchResponse(BaseModel):
    """Response envelope for vehicle search endpoint."""
    results: List[VehicleSearchResult] = []
    total: int = 0

