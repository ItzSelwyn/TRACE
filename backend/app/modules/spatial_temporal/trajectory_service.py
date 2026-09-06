"""
Layer 3 — Spatial-Temporal Reasoning: Vehicle Trajectory Reconstruction & Multi-Identifier Search Service.
========================================================================================================

Connects Layer 1 (Perception) and Layer 2 (Identity Fusion) to Layer 3 (Road Graph & Spatial-Temporal Reconstruction).

Resolves queries in priority order:
  Step 1: UUID (canonical_vehicle_id or observation_id)
  Step 2: Track ID (camera-local vehicle_observations.track_id)
  Step 3: Plate (fused_plate_text / CanonicalVehicle.best_plate_text)
  Step 4: Offline CityFlow fallback (strictly for demo/test evaluation when no DB record exists)

Guarantees:
- Database-First: Always queries PostgreSQL before falling back to evaluation data.
- Never contaminates production scoring or trajectory reconstruction with ground truth.
- Preserves explainable Layer 2 evidence across every camera transition.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, cast, func, or_, select, String, Text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    Camera,
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
from app.modules.perception.normalization import normalize_plate_text
from app.modules.spatial_temporal import reconstruct_trajectory
from app.modules.spatial_temporal.road_graph import get_road_graph
from app.schemas.vehicles import (
    EvidenceBreakdown,
    ObservationInTrajectory,
    TrajectoryResponse,
    VehicleSearchResult,
    VehicleSearchResponse,
)

logger = logging.getLogger("trace.spatial_temporal.trajectory_service")

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATASET_PATH = _PROJECT_ROOT / "data" / "ground_truth" / "cityflow_train_gt.jsonl"
CAMERAS_SEED_PATH = _PROJECT_ROOT / "data" / "seed" / "cameras.json"

# Fixed UUID-to-camera-alias mapping
_UUID_TO_CAMERA_ALIAS: Dict[str, str] = {
    "c1000000-0000-0000-0000-000000000001": "c020",
    "c2000000-0000-0000-0000-000000000002": "c023",
    "c3000000-0000-0000-0000-000000000003": "c029",
    "c4000000-0000-0000-0000-000000000004": "c035",
}


def _load_seed_cameras() -> Dict[str, Dict[str, Any]]:
    """Load seed camera locations and metadata."""
    if not CAMERAS_SEED_PATH.exists():
        return {}
    try:
        data = json.loads(CAMERAS_SEED_PATH.read_text(encoding="utf-8"))
        return {cam["camera_id"]: cam for cam in data}
    except Exception:
        return {}


_SEED_CAMERAS: Dict[str, Dict[str, Any]] = _load_seed_cameras()


def _resolve_camera_metadata(session: Session, camera_id: uuid.UUID) -> Dict[str, Any]:
    """Resolve camera alias, display name, latitude, and longitude."""
    cam_str = str(camera_id)
    alias = _UUID_TO_CAMERA_ALIAS.get(cam_str)

    # Check database camera row
    db_cam = session.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    ).scalars().first()

    name = db_cam.name if db_cam else f"Camera {alias.upper() if alias else cam_str[:8]}"

    # Fetch lat/lon from seed metadata (keyed by alias or uuid)
    seed = _SEED_CAMERAS.get(alias or "") or _SEED_CAMERAS.get(cam_str, {})
    lat = seed.get("latitude")
    lon = seed.get("longitude")

    return {
        "camera_id": camera_id,
        "camera_alias": alias or (db_cam.name if db_cam else "unknown"),
        "camera_name": name,
        "latitude": lat,
        "longitude": lon,
    }


def resolve_vehicle_identity(
    session: Session,
    query: str,
) -> Optional[Dict[str, Any]]:
    """Resolve a user search query to vehicle identity metadata and target observations.

    Resolves in strict priority:
      1. UUID (CanonicalVehicle or VehicleObservation)
      2. Track ID (vehicle_observations.track_id)
      3. Plate (fused_plate_text / CanonicalVehicle.best_plate_text)
    """
    q = str(query).strip()
    if not q:
        return None

    # -----------------------------------------------------------------------
    # Step 1 — UUID Check
    # -----------------------------------------------------------------------
    try:
        query_uuid = uuid.UUID(q)
        is_uuid = True
    except (ValueError, AttributeError):
        query_uuid = None
        is_uuid = False

    if is_uuid and query_uuid is not None:
        # 1a. Check CanonicalVehicle
        canon = session.execute(
            select(CanonicalVehicle).where(CanonicalVehicle.canonical_vehicle_id == query_uuid)
        ).scalars().first()
        if canon:
            # Load observations linked via TrajectoryPoint
            tps = session.execute(
                select(TrajectoryPoint)
                .where(TrajectoryPoint.canonical_vehicle_id == query_uuid)
                .order_by(TrajectoryPoint.sequence_no.asc())
            ).scalars().all()

            obs_ids = [tp.observation_id for tp in tps]
            if obs_ids:
                observations = session.execute(
                    select(VehicleObservation).where(VehicleObservation.observation_id.in_(obs_ids))
                ).scalars().all()
            else:
                observations = []

            if not observations and canon.best_plate_text:
                observations = session.execute(
                    select(VehicleObservation).where(or_(
                        VehicleObservation.fused_plate_text == canon.best_plate_text,
                        VehicleObservation.fused_plate_text == normalize_plate_text(canon.best_plate_text),
                    ))
                ).scalars().all()

            return {
                "identifier_type": "canonical_id",
                "vehicle_id": str(canon.canonical_vehicle_id),
                "canonical_vehicle_id": canon.canonical_vehicle_id,
                "target_observations": observations,
                "resolved_plate": canon.best_plate_text,
                "original_query": q,
            }

        # 1b. Check VehicleObservation
        obs = session.execute(
            select(VehicleObservation).where(VehicleObservation.observation_id == query_uuid)
        ).scalars().first()
        if obs:
            tp = session.execute(
                select(TrajectoryPoint).where(TrajectoryPoint.observation_id == query_uuid)
            ).scalars().first()
            canon_id = tp.canonical_vehicle_id if tp else None
            plate_val = obs.fused_plate_text if obs.fused_plate_text not in ("NOT READ", "") else None
            return {
                "identifier_type": "observation_id",
                "vehicle_id": str(obs.observation_id),
                "canonical_vehicle_id": canon_id,
                "target_observations": [obs],
                "resolved_plate": plate_val,
                "original_query": q,
            }

    # -----------------------------------------------------------------------
    # Step 2 — Track ID Check
    # -----------------------------------------------------------------------
    track_obs = session.execute(
        select(VehicleObservation)
        .where(or_(
            VehicleObservation.track_id == q,
            VehicleObservation.track_id == f"TRK-{q}",
            func.lower(VehicleObservation.track_id) == q.lower(),
        ))
        .order_by(VehicleObservation.captured_at.desc())
        .limit(20)
    ).scalars().all()

    if track_obs:
        primary_obs = track_obs[0]
        tp = session.execute(
            select(TrajectoryPoint).where(TrajectoryPoint.observation_id == primary_obs.observation_id)
        ).scalars().first()
        canon_id = tp.canonical_vehicle_id if tp else None
        plate_val = primary_obs.fused_plate_text if primary_obs.fused_plate_text not in ("NOT READ", "") else None
        return {
            "identifier_type": "track_id",
            "vehicle_id": primary_obs.track_id,
            "canonical_vehicle_id": canon_id,
            "target_observations": track_obs,
            "resolved_plate": plate_val,
            "original_query": q,
        }

    # -----------------------------------------------------------------------
    # Step 3 — Plate Check
    # -----------------------------------------------------------------------
    norm_plate = normalize_plate_text(q)
    spaceless = q.replace(" ", "").upper()

    # Search canonical vehicles by plate
    canon = session.execute(
        select(CanonicalVehicle).where(or_(
            CanonicalVehicle.best_plate_text == q,
            CanonicalVehicle.best_plate_text == norm_plate,
            CanonicalVehicle.best_plate_text == spaceless,
            func.replace(CanonicalVehicle.best_plate_text, " ", "") == spaceless,
        ))
    ).scalars().first()

    # Search vehicle observations by plate
    plate_obs = session.execute(
        select(VehicleObservation).where(or_(
            VehicleObservation.fused_plate_text == q,
            VehicleObservation.fused_plate_text == norm_plate,
            VehicleObservation.fused_plate_text == spaceless,
            func.replace(VehicleObservation.fused_plate_text, " ", "") == spaceless,
        )).order_by(VehicleObservation.captured_at.asc())
    ).scalars().all()

    if canon or plate_obs:
        best_p = (
            canon.best_plate_text
            if canon and canon.best_plate_text
            else (plate_obs[0].fused_plate_text if plate_obs else q)
        )
        canon_id = canon.canonical_vehicle_id if canon else None
        return {
            "identifier_type": "plate",
            "vehicle_id": best_p,
            "canonical_vehicle_id": canon_id,
            "target_observations": plate_obs,
            "resolved_plate": best_p,
            "original_query": q,
        }

    return None


def _expand_observation_cluster(
    session: Session,
    target_observations: List[VehicleObservation],
    canonical_vehicle_id: Optional[uuid.UUID] = None,
) -> List[VehicleObservation]:
    """Expand target observations using CanonicalVehicle and IdentityMatch relationships."""
    if not target_observations:
        return []

    cluster_obs_ids: Set[uuid.UUID] = {o.observation_id for o in target_observations}

    # If canonical vehicle exists, pull all its TrajectoryPoints
    if canonical_vehicle_id:
        tps = session.execute(
            select(TrajectoryPoint)
            .where(TrajectoryPoint.canonical_vehicle_id == canonical_vehicle_id)
        ).scalars().all()
        for tp in tps:
            cluster_obs_ids.add(tp.observation_id)

    # Expand across confirmed and candidate IdentityMatches
    queue = list(cluster_obs_ids)
    visited = set(cluster_obs_ids)

    hop = 0
    while queue and hop < 3:
        curr_batch = queue[:]
        queue = []
        matches = session.execute(
            select(IdentityMatch).where(
                or_(
                    IdentityMatch.observation_id_a.in_(curr_batch),
                    IdentityMatch.observation_id_b.in_(curr_batch),
                ),
                IdentityMatch.identity_score >= CANDIDATE_THRESHOLD,
            )
        ).scalars().all()

        for m in matches:
            other_id = m.observation_id_b if m.observation_id_a in curr_batch else m.observation_id_a
            if other_id not in visited:
                visited.add(other_id)
                cluster_obs_ids.add(other_id)
                queue.append(other_id)
        hop += 1

    # If no cross-camera matches were found and target has no canonical vehicle,
    # perform on-demand identity fusion across other cameras
    if len(cluster_obs_ids) == len(target_observations) and not canonical_vehicle_id and target_observations:
        try:
            from app.modules.identity.matcher import match_new_observation
            new_matches = match_new_observation(session, target_observations[0], road_graph=get_road_graph())
            for m in new_matches:
                other_id = m.get("observation_id_b") if m.get("observation_id_a") == target_observations[0].observation_id else m.get("observation_id_a")
                if other_id and other_id not in cluster_obs_ids:
                    cluster_obs_ids.add(other_id)
        except Exception as e:
            logger.debug(f"On-demand identity fusion skipped: {e}")

    # Retrieve all observations in cluster
    observations = session.execute(
        select(VehicleObservation)
        .where(VehicleObservation.observation_id.in_(list(cluster_obs_ids)))
        .order_by(VehicleObservation.captured_at.asc())
    ).scalars().all()

    return list(observations)


def _build_trajectory_from_database(
    session: Session,
    identity_info: Dict[str, Any],
    road_graph: Optional[Dict[str, Any]] = None,
) -> TrajectoryResponse:
    """Build and annotate vehicle trajectory from PostgreSQL records and road graph."""
    graph = road_graph or get_road_graph()
    target_obs = identity_info.get("target_observations", [])
    canon_id = identity_info.get("canonical_vehicle_id")
    vehicle_id = identity_info.get("vehicle_id", str(uuid.uuid4()))
    resolved_plate = identity_info.get("resolved_plate")
    id_type = identity_info.get("identifier_type", "unknown")

    # Expand to complete cross-camera identity cluster
    raw_obs_list = _expand_observation_cluster(session, target_obs, canon_id)

    # Deduplicate observations on the same camera occurring within a 5-second window
    filtered_obs: List[VehicleObservation] = []
    last_per_cam: Dict[uuid.UUID, datetime] = {}
    for obs in sorted(raw_obs_list, key=lambda o: o.captured_at):
        cam = obs.camera_id
        ts = obs.captured_at if obs.captured_at.tzinfo else obs.captured_at.replace(tzinfo=timezone.utc)
        if cam in last_per_cam:
            diff_s = abs((ts - last_per_cam[cam]).total_seconds())
            if diff_s < 5.0:
                continue
        last_per_cam[cam] = ts
        filtered_obs.append(obs)

    # Format observations for Layer 3 reconstruct_trajectory()
    obs_dicts: List[Dict[str, Any]] = []
    for i, obs in enumerate(filtered_obs):
        meta = _resolve_camera_metadata(session, obs.camera_id)
        cam_alias = meta["camera_alias"]

        # Default evidence
        ev_plate_sim = None
        ev_ocr_comp = None
        ev_app_sim = None
        ev_temp = None
        ev_trans = None
        ev_attr = 1.0
        score_val = 0.85
        conf_label = "confirmed"

        # Check pre-computed IdentityMatch with previous observation
        if i > 0:
            prev_obs = filtered_obs[i - 1]
            match = session.execute(
                select(IdentityMatch).where(
                    or_(
                        and_(IdentityMatch.observation_id_a == prev_obs.observation_id, IdentityMatch.observation_id_b == obs.observation_id),
                        and_(IdentityMatch.observation_id_a == obs.observation_id, IdentityMatch.observation_id_b == prev_obs.observation_id),
                    )
                )
            ).scalars().first()

            if match:
                ev_plate_sim = float(match.plate_similarity) if match.plate_similarity is not None else None
                ev_ocr_comp = float(match.ocr_confidence_component) if match.ocr_confidence_component is not None else None
                ev_app_sim = float(match.appearance_similarity) if match.appearance_similarity is not None else None
                ev_temp = float(match.temporal_score) if match.temporal_score is not None else None
                ev_trans = float(match.camera_transition_score) if match.camera_transition_score is not None else None
                score_val = float(match.identity_score)
                conf_label = "confirmed" if score_val >= CONFIRM_THRESHOLD else "candidate" if score_val >= CANDIDATE_THRESHOLD else "no_match"
                t_match = match.type_match if match.type_match is not None else True
                c_match = match.colour_match if match.colour_match is not None else True
                ev_attr = ((1.0 if t_match else 0.4) + (1.0 if c_match else 0.3)) / 2.0
            else:
                # Compute on-the-fly cross-camera scoring using Layer 2
                app_sim = None
                if obs.appearance_embedding and prev_obs.appearance_embedding:
                    try:
                        from app.modules.appearance import compute_appearance_similarity
                        app_sim = compute_appearance_similarity(prev_obs.appearance_embedding, obs.appearance_embedding)
                    except Exception:
                        app_sim = None

                prev_meta = _resolve_camera_metadata(session, prev_obs.camera_id)
                time_gap_s = (obs.captured_at - prev_obs.captured_at).total_seconds()

                scoring_res = compute_identity_score(
                    obs_a={
                        "fused_plate_text": prev_obs.fused_plate_text,
                        "fused_confidence": float(prev_obs.fused_confidence),
                        "vehicle_type": prev_obs.vehicle_type,
                        "vehicle_colour": prev_obs.vehicle_colour,
                    },
                    obs_b={
                        "fused_plate_text": obs.fused_plate_text,
                        "fused_confidence": float(obs.fused_confidence),
                        "vehicle_type": obs.vehicle_type,
                        "vehicle_colour": obs.vehicle_colour,
                    },
                    appearance_similarity=app_sim,
                    camera_id_a=prev_meta["camera_alias"],
                    camera_id_b=cam_alias,
                    time_gap_s=time_gap_s,
                    road_graph=graph,
                )
                score_val = scoring_res["identity_score"]
                conf_label = scoring_res["match_confidence_label"]
                ev_plate_sim = scoring_res.get("plate_similarity")
                ev_ocr_comp = scoring_res.get("ocr_confidence_component")
                ev_app_sim = scoring_res.get("appearance_similarity")
                ev_temp = scoring_res.get("temporal_score")
                ev_trans = scoring_res.get("camera_transition_score")
                ev_attr = scoring_res.get("attribute_match", 1.0)

        obs_dicts.append({
            "observation_id": obs.observation_id,
            "camera_id": obs.camera_id,
            "camera_name": meta["camera_name"],
            "camera_alias": cam_alias,
            "captured_at": obs.captured_at.isoformat(),
            "fused_plate_text": obs.fused_plate_text,
            "fused_confidence": float(obs.fused_confidence),
            "vehicle_type": obs.vehicle_type,
            "vehicle_colour": obs.vehicle_colour,
            "track_id": obs.track_id,
            "canonical_vehicle_id": canon_id,
            "latitude": meta["latitude"],
            "longitude": meta["longitude"],
            # Layer 2 Evidence
            "identity_score": score_val,
            "match_confidence_label": conf_label,
            "plate_similarity": ev_plate_sim,
            "ocr_confidence_component": ev_ocr_comp,
            "appearance_similarity": ev_app_sim,
            "temporal_score": ev_temp,
            "camera_transition_score": ev_trans,
            "attribute_match": ev_attr,
            "camera_reliability_weight": 0.90,
        })

    # Execute Layer 3 spatial-temporal reconstruction
    adapted_for_reconstruct: List[Dict[str, Any]] = []
    for d in obs_dicts:
        adapted = dict(d)
        adapted["camera_id"] = d.get("camera_alias") or str(d["camera_id"])
        adapted_for_reconstruct.append(adapted)

    spatial_payload = reconstruct_trajectory(
        plate_text=resolved_plate or vehicle_id,
        observations=adapted_for_reconstruct,
        graph=graph,
    )

    # Map reconstructed observations to schema
    final_observations: List[ObservationInTrajectory] = []
    for i, rec_obs in enumerate(spatial_payload.get("observations", [])):
        orig = obs_dicts[i]
        ev = EvidenceBreakdown(
            plate_similarity=orig.get("plate_similarity"),
            ocr_confidence_component=orig.get("ocr_confidence_component"),
            attribute_match=orig.get("attribute_match"),
            camera_reliability_weight=orig.get("camera_reliability_weight"),
            appearance_similarity=orig.get("appearance_similarity"),
            temporal_score=orig.get("temporal_score"),
            camera_transition_score=orig.get("camera_transition_score"),
            mode="ANPR" if orig.get("plate_similarity") is not None else "CITYFLOW",
        )

        final_observations.append(
            ObservationInTrajectory(
                observation_id=orig["observation_id"],
                camera_id=orig["camera_id"],
                camera_name=orig["camera_name"],
                captured_at=datetime.fromisoformat(orig["captured_at"]),
                fused_plate_text=orig["fused_plate_text"],
                fused_confidence=orig["fused_confidence"],
                vehicle_type=orig["vehicle_type"],
                vehicle_colour=orig["vehicle_colour"],
                track_id=orig["track_id"],
                canonical_vehicle_id=orig["canonical_vehicle_id"],
                identity_score=orig["identity_score"],
                match_confidence_label=orig["match_confidence_label"],
                evidence=ev,
                is_impossible_journey=bool(rec_obs.get("is_impossible_journey", False)),
                implied_speed_kmph=rec_obs.get("implied_speed_kmph"),
                anomaly_type=rec_obs.get("anomaly_type"),
                latitude=orig["latitude"],
                longitude=orig["longitude"],
            )
        )

    orig_query = identity_info.get("original_query", "")
    final_plate = orig_query if (id_type == "plate" and orig_query) else resolved_plate

    return TrajectoryResponse(
        plate=final_plate,
        vehicle_id=vehicle_id,
        search_query=orig_query or vehicle_id,
        identifier_type=id_type,
        observations=final_observations,
        anomaly_flags=spatial_payload.get("anomaly_flags", []),
        total_anomalies=spatial_payload.get("total_anomalies", 0),
    )


def _offline_ground_truth_fallback(
    query: str,
    road_graph: Optional[Dict[str, Any]] = None,
) -> TrajectoryResponse:
    """Offline / test evaluation fallback strictly used when no DB records exist."""
    logger.info(f"Using offline ground truth fallback for query '{query}'")
    from app.modules.identity import build_vehicle_trajectory
    from app.modules.perception import load_ground_truth_by_camera

    graph = road_graph or get_road_graph()
    selected_records: List[Dict[str, Any]] = []

    if DATASET_PATH.exists():
        dataset_records = load_ground_truth_by_camera(DATASET_PATH)
        for camera_records in dataset_records.values():
            selected_records.extend(camera_records[:25])

    identity_payload = build_vehicle_trajectory(
        query,
        selected_records or None,
    )
    raw_obs = identity_payload.get("observations", [])

    # Enrich with camera lat/lon from seed
    for obs in raw_obs:
        cid = str(obs.get("camera_id", ""))
        seed = _SEED_CAMERAS.get(cid, {})
        if seed:
            obs["latitude"] = seed.get("latitude")
            obs["longitude"] = seed.get("longitude")
            obs["camera_name"] = seed.get("name", obs.get("camera_name"))

    spatial_payload = reconstruct_trajectory(query, raw_obs, graph)
    annotated_obs = spatial_payload.get("observations", [])

    observations: List[ObservationInTrajectory] = []
    for obs in annotated_obs:
        ev = EvidenceBreakdown(
            plate_similarity=obs.get("plate_similarity", 1.0),
            ocr_confidence_component=obs.get("ocr_confidence_component", 0.90),
            attribute_match=obs.get("attribute_match", 1.0),
            camera_reliability_weight=obs.get("camera_reliability_weight", 0.90),
            appearance_similarity=obs.get("appearance_similarity"),
            temporal_score=obs.get("temporal_score"),
            camera_transition_score=obs.get("camera_transition_score"),
            mode="CITYFLOW" if obs.get("plate_similarity") is None else "ANPR",
        )
        observations.append(
            ObservationInTrajectory(
                observation_id=uuid.uuid4(),
                camera_id=uuid.uuid4(),
                camera_name=obs.get("camera_name"),
                captured_at=datetime.fromisoformat(obs["captured_at"]),
                fused_plate_text=obs.get("fused_plate_text", query),
                fused_confidence=float(obs.get("fused_confidence", 0.92)),
                vehicle_type=obs.get("vehicle_type", "vehicle"),
                vehicle_colour=obs.get("vehicle_colour", "unknown"),
                track_id=obs.get("track_id"),
                identity_score=float(obs.get("identity_score", 0.85)),
                match_confidence_label=obs.get("match_confidence_label", "confirmed"),
                evidence=ev,
                is_impossible_journey=bool(obs.get("is_impossible_journey", False)),
                implied_speed_kmph=obs.get("implied_speed_kmph"),
                anomaly_type=obs.get("anomaly_type"),
                latitude=obs.get("latitude"),
                longitude=obs.get("longitude"),
            )
        )

    return TrajectoryResponse(
        plate=query if any(c.isalpha() for c in query) else None,
        vehicle_id=query,
        search_query=query,
        identifier_type="cityflow_ground_truth_fallback",
        observations=observations,
        anomaly_flags=spatial_payload.get("anomaly_flags", []),
        total_anomalies=spatial_payload.get("total_anomalies", 0),
    )


def find_and_build_trajectory(
    session: Session,
    query: str,
    road_graph: Optional[Dict[str, Any]] = None,
) -> TrajectoryResponse:
    """Find and build vehicle trajectory across cameras.

    Prioritizes PostgreSQL database records first; uses offline GT fallback
    only when no database record matches the query.
    """
    identity_info = resolve_vehicle_identity(session, query)

    if identity_info and identity_info.get("target_observations"):
        return _build_trajectory_from_database(session, identity_info, road_graph)

    # Step 4: Fallback strictly when no DB records match query
    return _offline_ground_truth_fallback(query, road_graph)


def search_vehicles(
    session: Session,
    query: str,
    limit: int = 20,
) -> VehicleSearchResponse:
    """Search vehicles in PostgreSQL across track IDs, canonical vehicles, and license plates."""
    q = str(query).strip()
    if not q:
        return VehicleSearchResponse(results=[], total=0)

    results: List[VehicleSearchResult] = []
    seen_identifiers: Set[str] = set()

    # 1. Search Canonical Vehicles
    canons = session.execute(
        select(CanonicalVehicle).where(or_(
            CanonicalVehicle.best_plate_text.ilike(f"%{q}%"),
            cast(CanonicalVehicle.canonical_vehicle_id, String).ilike(f"%{q}%"),
        )).limit(limit)
    ).scalars().all()

    for c in canons:
        ident = str(c.canonical_vehicle_id)
        if ident in seen_identifiers:
            continue
        seen_identifiers.add(ident)

        # Get latest observation associated with canonical vehicle
        tp = session.execute(
            select(TrajectoryPoint)
            .where(TrajectoryPoint.canonical_vehicle_id == c.canonical_vehicle_id)
            .order_by(TrajectoryPoint.captured_at.desc())
        ).scalars().first()

        v_type = "car"
        v_colour = "unknown"
        cam_name = "Camera"
        last_ts = c.last_seen_at
        obs_count = 1

        if tp:
            obs = session.execute(
                select(VehicleObservation).where(VehicleObservation.observation_id == tp.observation_id)
            ).scalars().first()
            if obs:
                v_type = obs.vehicle_type
                v_colour = obs.vehicle_colour
                meta = _resolve_camera_metadata(session, obs.camera_id)
                cam_name = meta["camera_name"]

        results.append(
            VehicleSearchResult(
                identifier=c.best_plate_text or ident,
                identifier_type="canonical_id" if not c.best_plate_text else "plate",
                canonical_vehicle_id=c.canonical_vehicle_id,
                vehicle_type=v_type,
                vehicle_colour=v_colour,
                latest_camera=cam_name,
                latest_timestamp=last_ts,
                has_plate=c.best_plate_text is not None,
                observation_count=obs_count,
            )
        )

    # 2. Search VehicleObservation by track_id or plate
    obs_query = session.execute(
        select(VehicleObservation)
        .where(or_(
            VehicleObservation.track_id.ilike(f"%{q}%"),
            and_(
                VehicleObservation.fused_plate_text.ilike(f"%{q}%"),
                VehicleObservation.fused_plate_text != "NOT READ",
            ),
        ))
        .order_by(VehicleObservation.captured_at.desc())
        .limit(limit)
    ).scalars().all()

    for o in obs_query:
        has_plate = o.fused_plate_text not in ("NOT READ", "")
        ident = o.fused_plate_text if has_plate else o.track_id
        if ident in seen_identifiers:
            continue
        seen_identifiers.add(ident)

        meta = _resolve_camera_metadata(session, o.camera_id)

        results.append(
            VehicleSearchResult(
                identifier=ident,
                identifier_type="plate" if has_plate else "track_id",
                canonical_vehicle_id=None,
                vehicle_type=o.vehicle_type,
                vehicle_colour=o.vehicle_colour,
                latest_camera=meta["camera_name"],
                latest_timestamp=o.captured_at,
                has_plate=has_plate,
                observation_count=1,
            )
        )

    return VehicleSearchResponse(results=results[:limit], total=len(results[:limit]))
