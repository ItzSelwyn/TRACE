"""Layer 2 — Identity Fusion Module: Cross-Camera Matching and Database Persistence.

Uses the multi-modal scoring engine (scoring.py) to compare observations.
Temporal and camera-transition evidence is derived from the spatial_temporal
road graph already present in the project — no duplication.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    Camera,
    CameraReliabilityProfile,
    CanonicalVehicle,
    IdentityMatch,
    TrajectoryPoint,
    VehicleObservation,
)
from app.modules.identity.scoring import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    compute_identity_score,
)

logger = logging.getLogger("trace.identity.matcher")

# ---------------------------------------------------------------------------
# Camera alias map — mirrors persistence.py to convert UUID back to short ID
# for road-graph lookups
# ---------------------------------------------------------------------------
_UUID_TO_CAMERA_ALIAS: Dict[str, str] = {
    "c1000000-0000-0000-0000-000000000001": "c020",
    "c2000000-0000-0000-0000-000000000002": "c023",
    "c3000000-0000-0000-0000-000000000003": "c029",
    "c4000000-0000-0000-0000-000000000004": "c035",
}


def _camera_uuid_to_alias(camera_uuid: uuid.UUID) -> Optional[str]:
    """Convert a camera UUID to a road-graph alias string (e.g. c029), or None."""
    return _UUID_TO_CAMERA_ALIAS.get(str(camera_uuid))


def load_camera_reliability_profiles(session: Session) -> Dict[str, Dict[str, float]]:
    """Load all camera reliability profiles keyed by camera_id (UUID string)."""
    profiles: Dict[str, Dict[str, float]] = {}
    try:
        rows = session.execute(select(CameraReliabilityProfile)).scalars().all()
        for r in rows:
            profiles[str(r.camera_id)] = {
                "day_ocr_reliability": float(r.day_ocr_reliability),
                "night_ocr_reliability": float(r.night_ocr_reliability),
                "rain_ocr_reliability": float(r.rain_ocr_reliability),
                "angle_ocr_reliability": float(r.angle_ocr_reliability),
            }
    except Exception as e:
        logger.warning(f"Could not load camera reliability profiles: {e}")
    return profiles


def _compute_time_gap(
    obs_a: VehicleObservation,
    obs_b: VehicleObservation,
) -> Optional[float]:
    """Return seconds between two observation timestamps, or None on failure."""
    try:
        ts_a = obs_a.captured_at
        ts_b = obs_b.captured_at
        if ts_a.tzinfo is None:
            ts_a = ts_a.replace(tzinfo=timezone.utc)
        if ts_b.tzinfo is None:
            ts_b = ts_b.replace(tzinfo=timezone.utc)
        return (ts_b - ts_a).total_seconds()
    except Exception:
        return None


def match_observation_pair(
    session: Session,
    obs_a: VehicleObservation,
    obs_b: VehicleObservation,
    profiles: Optional[Dict[str, Dict[str, float]]] = None,
    persist: bool = True,
    verbose: bool = False,
    commit: bool = True,
    appearance_similarity: Optional[float] = None,
    road_graph: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Score a pair of observations and optionally persist to identity_matches.

    Guarantees:
    - Self-comparison returns None.
    - Symmetrical UUID ordering prevents duplicate rows.
    - Works without plates (CityFlowV2), or with plates (ANPR).
    """
    if obs_a.observation_id == obs_b.observation_id:
        return None

    prof_a = (profiles or {}).get(str(obs_a.camera_id))
    prof_b = (profiles or {}).get(str(obs_b.camera_id))

    # Resolve camera alias strings for road-graph lookups
    cam_a_alias = _camera_uuid_to_alias(obs_a.camera_id)
    cam_b_alias = _camera_uuid_to_alias(obs_b.camera_id)

    # Compute temporal gap
    time_gap_s = _compute_time_gap(obs_a, obs_b)

    dict_a = {
        "fused_plate_text": obs_a.fused_plate_text,
        "fused_confidence": float(obs_a.fused_confidence),
        "vehicle_type": obs_a.vehicle_type,
        "vehicle_colour": obs_a.vehicle_colour,
        "captured_at": obs_a.captured_at,
        "camera_id": cam_a_alias or str(obs_a.camera_id),
    }
    dict_b = {
        "fused_plate_text": obs_b.fused_plate_text,
        "fused_confidence": float(obs_b.fused_confidence),
        "vehicle_type": obs_b.vehicle_type,
        "vehicle_colour": obs_b.vehicle_colour,
        "captured_at": obs_b.captured_at,
        "camera_id": cam_b_alias or str(obs_b.camera_id),
    }

    # Resolve appearance similarity from stored embeddings if not explicitly provided
    app_sim = appearance_similarity
    if app_sim is None:
        emb_a = getattr(obs_a, "appearance_embedding", None)
        emb_b = getattr(obs_b, "appearance_embedding", None)
        if emb_a is not None and emb_b is not None:
            try:
                from app.modules.appearance import compute_appearance_similarity
                app_sim = compute_appearance_similarity(emb_a, emb_b)
            except Exception as e:
                logger.debug(f"Could not compute appearance similarity: {e}")
                app_sim = None

    evidence = compute_identity_score(
        dict_a,
        dict_b,
        camera_profile_a=prof_a,
        camera_profile_b=prof_b,
        appearance_similarity=app_sim,
        camera_id_a=cam_a_alias,
        camera_id_b=cam_b_alias,
        time_gap_s=time_gap_s,
        road_graph=road_graph,
    )
    score = evidence["identity_score"]
    status = evidence["status"]

    # Log only candidate/confirmed matches to avoid flooding logs
    if score >= CANDIDATE_THRESHOLD or verbose:
        logger.info(
            "[IDENTITY] obs_a=%s obs_b=%s plate_a=%r plate_b=%r mode=%s "
            "appearance=%s temporal=%.3f cam_trans=%s score=%.3f status=%s",
            obs_a.observation_id,
            obs_b.observation_id,
            evidence.get("plate_a"),
            evidence.get("plate_b"),
            evidence.get("mode"),
            evidence.get("appearance_similarity"),
            evidence.get("temporal_score") or 0.0,
            evidence.get("camera_transition_score"),
            score,
            status,
        )

    if not persist:
        return {
            "observation_id_a": obs_a.observation_id,
            "observation_id_b": obs_b.observation_id,
            **evidence,
        }

    if score >= CANDIDATE_THRESHOLD:
        id_1, id_2 = sorted([obs_a.observation_id, obs_b.observation_id])

        existing = session.execute(
            select(IdentityMatch).where(
                or_(
                    (IdentityMatch.observation_id_a == id_1) & (IdentityMatch.observation_id_b == id_2),
                    (IdentityMatch.observation_id_a == id_2) & (IdentityMatch.observation_id_b == id_1),
                )
            )
        ).scalars().first()

        plate_sim = evidence.get("plate_similarity")
        ocr_comp = evidence.get("ocr_confidence_component")
        type_match = evidence.get("type_match")
        colour_match = evidence.get("colour_match")
        app_sim = evidence.get("appearance_similarity")
        temporal = evidence.get("temporal_score")
        cam_trans = evidence.get("camera_transition_score")

        if existing:
            existing.plate_similarity = round(plate_sim, 3) if plate_sim is not None else None
            existing.ocr_confidence_component = round(ocr_comp, 3) if ocr_comp is not None else None
            existing.type_match = type_match
            existing.colour_match = colour_match
            existing.appearance_similarity = round(app_sim, 3) if app_sim is not None else None
            existing.temporal_score = round(temporal, 3) if temporal is not None else None
            existing.camera_transition_score = round(cam_trans, 3) if cam_trans is not None else None
            existing.identity_score = round(score, 3)
            match_record = existing
        else:
            match_record = IdentityMatch(
                match_id=uuid.uuid4(),
                observation_id_a=id_1,
                observation_id_b=id_2,
                plate_similarity=round(plate_sim, 3) if plate_sim is not None else None,
                ocr_confidence_component=round(ocr_comp, 3) if ocr_comp is not None else None,
                type_match=type_match,
                colour_match=colour_match,
                appearance_similarity=round(app_sim, 3) if app_sim is not None else None,
                temporal_score=round(temporal, 3) if temporal is not None else None,
                camera_transition_score=round(cam_trans, 3) if cam_trans is not None else None,
                identity_score=round(score, 3),
                implied_speed_kmph=None,
                is_impossible_journey=(temporal == 0.0),
            )
            session.add(match_record)

        if commit:
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


def run_identity_fusion_on_database(
    session: Session,
    readable_only: bool = True,
    limit: Optional[int] = None,
    verbose: bool = False,
    road_graph: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute cross-camera identity fusion on vehicle_observations in PostgreSQL.

    Parameters
    ----------
    readable_only : When True, only considers observations with readable plates.
                   When False, includes all observations (CityFlowV2 mode).
    limit         : Safety bound on number of observations processed.
    verbose       : Log all pairs, not just matches.
    road_graph    : Pre-loaded road graph (lazy-loaded if None).
    """
    # Pre-load graph once per batch
    if road_graph is None:
        try:
            from app.modules.spatial_temporal.road_graph import get_road_graph
            road_graph = get_road_graph()
        except Exception as e:
            logger.warning(f"Road graph unavailable: {e}")
            road_graph = None

    profiles = load_camera_reliability_profiles(session)
    total_db_count = session.scalar(select(func.count(VehicleObservation.observation_id))) or 0

    query = select(VehicleObservation)
    if readable_only:
        query = query.where(
            VehicleObservation.fused_plate_text.is_not(None),
            VehicleObservation.fused_plate_text != "NOT READ",
            VehicleObservation.fused_plate_text != "",
        )
    query = query.order_by(VehicleObservation.captured_at.asc())
    if limit is not None:
        query = query.limit(limit)

    observations = session.execute(query).scalars().all()

    if not observations or len(observations) < 2:
        return {
            "total_db_observations": total_db_count,
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

    n = len(observations)
    for i in range(n):
        for j in range(i + 1, n):
            obs_a = observations[i]
            obs_b = observations[j]

            if obs_a.camera_id == obs_b.camera_id:
                continue

            matches_evaluated += 1
            result = match_observation_pair(
                session,
                obs_a,
                obs_b,
                profiles=profiles,
                persist=True,
                verbose=verbose,
                commit=False,
                road_graph=road_graph,
            )
            if result and result.get("identity_score", 0.0) >= CONFIRM_THRESHOLD:
                confirmed_matches += 1
                confirmed_pairs.append((obs_a, obs_b))
            elif result and result.get("identity_score", 0.0) >= CANDIDATE_THRESHOLD:
                candidate_matches += 1

    session.commit()

    canonical_created = _update_canonical_vehicles(session, confirmed_pairs)

    return {
        "total_db_observations": total_db_count,
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
    """Group confirmed pairs into connected components and upsert CanonicalVehicle records.

    Canonical vehicles can exist without a plate (best_plate_text = None).
    When a readable plate is available, the highest-confidence plate is used.
    """
    if not confirmed_pairs:
        return 0

    adj: Dict[uuid.UUID, Set[uuid.UUID]] = defaultdict(set)
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
        component: List[VehicleObservation] = []
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

        first_seen = min(o.captured_at for o in comp)
        last_seen = max(o.captured_at for o in comp)

        # Best plate: pick highest-confidence observation that has a readable plate
        from app.modules.identity.scoring import _is_plate_unavailable
        readable = [
            o for o in comp
            if not _is_plate_unavailable(o.fused_plate_text)
        ]
        if readable:
            best_obs = max(readable, key=lambda o: float(o.fused_confidence))
            best_plate: Optional[str] = best_obs.fused_plate_text
        else:
            best_plate = None  # CityFlowV2: no plate — canonical vehicle without plate

        # Try to find existing canonical vehicle:
        # 1. From existing TrajectoryPoints of any observation in the component
        canonical: Optional[CanonicalVehicle] = None
        for o in comp:
            existing_tp = session.execute(
                select(TrajectoryPoint).where(TrajectoryPoint.observation_id == o.observation_id)
            ).scalars().first()
            if existing_tp and existing_tp.canonical_vehicle_id:
                canonical = session.get(CanonicalVehicle, existing_tp.canonical_vehicle_id)
                if canonical:
                    break

        # 2. By plate text (if plate available and not yet found)
        if canonical is None and best_plate is not None:
            canonical = session.execute(
                select(CanonicalVehicle).where(CanonicalVehicle.best_plate_text == best_plate)
            ).scalars().first()

        if canonical:
            canonical.first_seen_at = min(canonical.first_seen_at, first_seen)
            canonical.last_seen_at = max(canonical.last_seen_at, last_seen)
            if canonical.best_plate_text is None and best_plate is not None:
                canonical.best_plate_text = best_plate
        else:
            canonical = CanonicalVehicle(
                canonical_vehicle_id=uuid.uuid4(),
                best_plate_text=best_plate,
                first_seen_at=first_seen,
                last_seen_at=last_seen,
            )
            session.add(canonical)
            session.flush()
            canonical_count += 1

        # Populate trajectory_points for the canonical vehicle
        sorted_comp = sorted(comp, key=lambda o: o.captured_at)
        for seq_no, obs in enumerate(sorted_comp, start=1):
            existing_tp = session.execute(
                select(TrajectoryPoint).where(
                    TrajectoryPoint.canonical_vehicle_id == canonical.canonical_vehicle_id,
                    TrajectoryPoint.observation_id == obs.observation_id,
                )
            ).scalars().first()
            if not existing_tp:
                tp = TrajectoryPoint(
                    trajectory_point_id=uuid.uuid4(),
                    canonical_vehicle_id=canonical.canonical_vehicle_id,
                    observation_id=obs.observation_id,
                    sequence_no=seq_no,
                    camera_id=obs.camera_id,
                    captured_at=obs.captured_at,
                )
                session.add(tp)

    session.commit()
    return canonical_count


def match_new_observation(
    session: Session,
    new_obs: VehicleObservation,
    max_candidates: int = 50,
    time_window_minutes: int = 60,
    road_graph: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Incrementally match a single new observation against recent observations from other cameras.

    Executes in real-time as observations are ingested from video feeds.
    Matches with score >= CANDIDATE_THRESHOLD (0.40) are saved to identity_matches.
    Matches with score >= CONFIRM_THRESHOLD (0.70) trigger CanonicalVehicle and TrajectoryPoint updates.
    """
    if road_graph is None:
        try:
            from app.modules.spatial_temporal.road_graph import get_road_graph
            road_graph = get_road_graph()
        except Exception:
            road_graph = None

    profiles = load_camera_reliability_profiles(session)

    # Time window around new_obs
    ts = new_obs.captured_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = timedelta(minutes=time_window_minutes)
    start_ts = ts - delta
    end_ts = ts + delta

    # Find candidates from other cameras
    candidates = session.execute(
        select(VehicleObservation).where(
            VehicleObservation.camera_id != new_obs.camera_id,
            VehicleObservation.captured_at >= start_ts,
            VehicleObservation.captured_at <= end_ts,
        )
        .order_by(VehicleObservation.captured_at.desc())
        .limit(max_candidates)
    ).scalars().all()

    if not candidates:
        return []

    confirmed_pairs: List[Tuple[VehicleObservation, VehicleObservation]] = []
    matches: List[Dict[str, Any]] = []

    for cand in candidates:
        res = match_observation_pair(
            session,
            cand,
            new_obs,
            profiles=profiles,
            persist=True,
            verbose=False,
            commit=False,
            road_graph=road_graph,
        )
        if res and res.get("identity_score", 0.0) >= CANDIDATE_THRESHOLD:
            matches.append(res)
            if res.get("identity_score", 0.0) >= CONFIRM_THRESHOLD:
                confirmed_pairs.append((cand, new_obs))

    if confirmed_pairs:
        _update_canonical_vehicles(session, confirmed_pairs)
    else:
        session.commit()

    return matches
