"""Layer 2 — Identity Fusion Module: Cross-Camera Matching, Duplicate Prevention, and Database Persistence."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Camera, CameraReliabilityProfile, CanonicalVehicle, IdentityMatch, VehicleObservation
from app.modules.identity.scoring import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    compute_identity_score,
)

logger = logging.getLogger("trace.identity.matcher")


def load_camera_reliability_profiles(session: Session) -> Dict[str, Dict[str, float]]:
    """Load all camera reliability profiles from database into a lookup dictionary keyed by camera_id (UUID string)."""
    profiles: Dict[str, Dict[str, float]] = {}
    try:
        rows = session.execute(select(CameraReliabilityProfile)).scalars().all()
        for r in rows:
            cam_key = str(r.camera_id)
            profiles[cam_key] = {
                "day_ocr_reliability": float(r.day_ocr_reliability),
                "night_ocr_reliability": float(r.night_ocr_reliability),
                "rain_ocr_reliability": float(r.rain_ocr_reliability),
                "angle_ocr_reliability": float(r.angle_ocr_reliability),
            }
    except Exception as e:
        logger.warning(f"Could not load camera reliability profiles from DB: {e}")
    return profiles


def match_observation_pair(
    session: Session,
    obs_a: VehicleObservation,
    obs_b: VehicleObservation,
    profiles: Optional[Dict[str, Dict[str, float]]] = None,
    persist: bool = True,
) -> Optional[Dict[str, Any]]:
    """Score a pair of vehicle observations and optionally persist/update identity_matches in PostgreSQL.
    
    Guarantees:
    - Never matches observation with itself.
    - Symmetrical canonical ID ordering prevents duplicate identity_matches rows.
    - Returns structured evidence breakdown and status (CONFIRMED / LOW_CONFIDENCE / NO_MATCH).
    """
    if obs_a.observation_id == obs_b.observation_id:
        return None  # Ignore self-comparison

    prof_a = profiles.get(str(obs_a.camera_id)) if profiles else None
    prof_b = profiles.get(str(obs_b.camera_id)) if profiles else None

    dict_a = {
        "fused_plate_text": obs_a.fused_plate_text,
        "fused_confidence": float(obs_a.fused_confidence),
        "vehicle_type": obs_a.vehicle_type,
        "vehicle_colour": obs_a.vehicle_colour,
        "captured_at": obs_a.captured_at,
    }
    dict_b = {
        "fused_plate_text": obs_b.fused_plate_text,
        "fused_confidence": float(obs_b.fused_confidence),
        "vehicle_type": obs_b.vehicle_type,
        "vehicle_colour": obs_b.vehicle_colour,
        "captured_at": obs_b.captured_at,
    }

    evidence = compute_identity_score(dict_a, dict_b, prof_a, prof_b)
    score = evidence["identity_score"]
    status = evidence["status"]

    # Structured Logging (Step 17)
    print(
        f"[IDENTITY] observation_a={obs_a.observation_id} observation_b={obs_b.observation_id} "
        f"plate_a='{evidence['plate_a']}' plate_b='{evidence['plate_b']}' "
        f"plate_sim={evidence['plate_similarity']:.3f} ocr_comp={evidence['ocr_confidence_component']:.3f} "
        f"type_match={evidence['type_match']} colour_match={evidence['colour_match']} "
        f"identity_score={score:.3f} status={status}"
    )

    if not persist:
        return {
            "observation_id_a": obs_a.observation_id,
            "observation_id_b": obs_b.observation_id,
            **evidence,
        }

    # Only persist candidate or confirmed matches (score >= CANDIDATE_THRESHOLD)
    if score >= CANDIDATE_THRESHOLD:
        # Canonical ordering: min UUID as observation_id_a, max UUID as observation_id_b
        id_1, id_2 = sorted([obs_a.observation_id, obs_b.observation_id])

        existing_match = session.execute(
            select(IdentityMatch).where(
                or_(
                    (IdentityMatch.observation_id_a == id_1) & (IdentityMatch.observation_id_b == id_2),
                    (IdentityMatch.observation_id_a == id_2) & (IdentityMatch.observation_id_b == id_1),
                )
            )
        ).scalars().first()

        if existing_match:
            # Update existing record (Step 9 Duplicate Prevention)
            existing_match.plate_similarity = round(evidence["plate_similarity"], 3)
            existing_match.ocr_confidence_component = round(evidence["ocr_confidence_component"], 3)
            existing_match.type_match = evidence["type_match"]
            existing_match.colour_match = evidence["colour_match"]
            existing_match.identity_score = round(score, 3)
            match_record = existing_match
        else:
            match_record = IdentityMatch(
                match_id=uuid.uuid4(),
                observation_id_a=id_1,
                observation_id_b=id_2,
                plate_similarity=round(evidence["plate_similarity"], 3),
                ocr_confidence_component=round(evidence["ocr_confidence_component"], 3),
                type_match=evidence["type_match"],
                colour_match=evidence["colour_match"],
                identity_score=round(score, 3),
                implied_speed_kmph=None,
                is_impossible_journey=False,
            )
            session.add(match_record)

        session.commit()
        return {
            "match_id": match_record.match_id,
            "observation_id_a": id_1,
            "observation_id_b": id_2,
            **evidence,
        }

    return {
        "observation_id_a": obs_a.observation_id,
        "observation_id_b": obs_b.observation_id,
        **evidence,
    }


def run_identity_fusion_on_database(session: Session) -> Dict[str, Any]:
    """Execute cross-camera identity fusion on all vehicle_observations in PostgreSQL.
    
    1. Loads observations from database.
    2. Compares all cross-camera observation pairs.
    3. Persists candidate and confirmed matches into identity_matches.
    4. Groups confirmed matches into canonical_vehicles.
    """
    profiles = load_camera_reliability_profiles(session)
    observations = session.execute(
        select(VehicleObservation).order_by(VehicleObservation.captured_at.asc())
    ).scalars().all()

    if not observations or len(observations) < 2:
        return {
            "observations_count": len(observations),
            "matches_evaluated": 0,
            "confirmed_matches": 0,
            "candidate_matches": 0,
            "canonical_vehicles_count": 0,
        }

    matches_evaluated = 0
    confirmed_matches = 0
    candidate_matches = 0

    confirmed_pairs: List[Tuple[VehicleObservation, VehicleObservation]] = []

    # Cross-camera pairwise comparison
    n = len(observations)
    for i in range(n):
        for j in range(i + 1, n):
            obs_a = observations[i]
            obs_b = observations[j]

            # Cross-camera only
            if obs_a.camera_id == obs_b.camera_id:
                continue

            matches_evaluated += 1
            result = match_observation_pair(session, obs_a, obs_b, profiles=profiles, persist=True)
            if result and result.get("identity_score", 0.0) >= CONFIRM_THRESHOLD:
                confirmed_matches += 1
                confirmed_pairs.append((obs_a, obs_b))
            elif result and result.get("identity_score", 0.0) >= CANDIDATE_THRESHOLD:
                candidate_matches += 1

    # Step 10 & 11: Group confirmed matches into CanonicalVehicle entities
    canonical_created = _update_canonical_vehicles(session, confirmed_pairs)

    return {
        "observations_count": len(observations),
        "matches_evaluated": matches_evaluated,
        "confirmed_matches": confirmed_matches,
        "candidate_matches": candidate_matches,
        "canonical_vehicles_count": canonical_created,
    }


def _update_canonical_vehicles(
    session: Session,
    confirmed_pairs: List[Tuple[VehicleObservation, VehicleObservation]],
) -> int:
    """Group confirmed observation pairs into connected components and persist/update CanonicalVehicle records."""
    if not confirmed_pairs:
        return 0

    # Build adjacency list for connected components (Step 11 Union/Grouping)
    adj = defaultdict(set)
    obs_map: Dict[uuid.UUID, VehicleObservation] = {}

    for obs_a, obs_b in confirmed_pairs:
        adj[obs_a.observation_id].add(obs_b.observation_id)
        adj[obs_b.observation_id].add(obs_a.observation_id)
        obs_map[obs_a.observation_id] = obs_a
        obs_map[obs_b.observation_id] = obs_b

    visited: Set[uuid.UUID] = set()
    components: List[List[VehicleObservation]] = []

    for obs_id in adj:
        if obs_id in visited:
            continue
        component = []
        queue = [obs_id]
        visited.add(obs_id)

        while queue:
            curr = queue.pop(0)
            component.append(obs_map[curr])
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(component)

    canonical_count = 0
    for comp in components:
        if not comp:
            continue

        # Determine best plate (highest confidence), first seen, and last seen
        best_obs = max(comp, key=lambda o: float(o.fused_confidence))
        best_plate = best_obs.fused_plate_text
        first_seen = min(o.captured_at for o in comp)
        last_seen = max(o.captured_at for o in comp)

        # Check if canonical vehicle already exists for this plate
        canonical = session.execute(
            select(CanonicalVehicle).where(CanonicalVehicle.best_plate_text == best_plate)
        ).scalars().first()

        if canonical:
            canonical.first_seen_at = min(canonical.first_seen_at, first_seen)
            canonical.last_seen_at = max(canonical.last_seen_at, last_seen)
        else:
            canonical = CanonicalVehicle(
                canonical_vehicle_id=uuid.uuid4(),
                best_plate_text=best_plate,
                first_seen_at=first_seen,
                last_seen_at=last_seen,
            )
            session.add(canonical)
            canonical_count += 1

    session.commit()
    return canonical_count

