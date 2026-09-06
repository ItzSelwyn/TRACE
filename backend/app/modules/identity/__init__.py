"""Layer 2 — Identity Fusion Module
================================
Multi-modal identity scoring for cross-camera vehicle matching and trajectory linking.

Modes:
    CityFlowV2 / visual-only (no plate required):
        appearance_similarity 55%
        temporal_score        25%
        camera_transition     15%
        colour_score           3%
        type_score             2%

    ANPR-capable (both plates readable):
        plate_similarity      35%
        appearance_similarity 30%
        temporal_score        15%
        camera_transition     10%
        colour_score           5%
        type_score             5%

Thresholds:
    >= 0.70     -> confirmed match
    0.40 - 0.70 -> candidate / low-confidence match
    < 0.40      -> no match
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.modules.identity.matcher import (
    _update_canonical_vehicles,
    load_camera_reliability_profiles,
    match_new_observation,
    match_observation_pair,
    run_identity_fusion_on_database,
)
from app.modules.identity.scoring import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    compute_identity_score,
    compute_temporal_score,
    compute_camera_transition_score,
    levenshtein_similarity,
    select_reliability,
)


def pair_observations(
    observations: List[Dict[str, Any]],
    camera_profiles: Optional[Dict[str, Dict[str, float]]] = None,
    appearance_similarities: Optional[Dict[str, float]] = None,
    road_graph: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Score every cross-camera pair and return candidate/confirmed matches.

    Args:
        observations:           list of observation dicts
        camera_profiles:        camera reliability profiles keyed by camera_id
        appearance_similarities: optional dict mapping (obs_i, obs_j) key to similarity
        road_graph:             pre-loaded road graph (lazy-loaded if None)
    """
    profiles = camera_profiles or {}
    app_sims = appearance_similarities or {}
    matches: List[Dict[str, Any]] = []
    n = len(observations)

    for i in range(n):
        for j in range(i + 1, n):
            obs_a = observations[i]
            obs_b = observations[j]
            if obs_a.get("camera_id") == obs_b.get("camera_id"):
                continue

            cam_id_a = str(obs_a.get("camera_id", ""))
            cam_id_b = str(obs_b.get("camera_id", ""))

            app_sim = app_sims.get((i, j)) or app_sims.get((j, i))

            result = compute_identity_score(
                obs_a,
                obs_b,
                camera_profile_a=profiles.get(cam_id_a),
                camera_profile_b=profiles.get(cam_id_b),
                appearance_similarity=app_sim,
                camera_id_a=cam_id_a,
                camera_id_b=cam_id_b,
                road_graph=road_graph,
            )

            if result["identity_score"] >= CANDIDATE_THRESHOLD:
                matches.append({
                    "obs_index_a": i,
                    "obs_index_b": j,
                    **result,
                })

    return sorted(matches, key=lambda m: m["identity_score"], reverse=True)


def build_vehicle_trajectory(
    plate_text: str,
    records: Optional[List[Dict[str, Any]]] = None,
    camera_profiles: Optional[Dict[str, Dict[str, float]]] = None,
    road_graph: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build trajectory observations payload with multi-modal identity evidence."""
    profiles = camera_profiles or {}
    camera_templates = ["c020", "c023", "c029", "c035"]
    source_records = list(records or [])

    if not source_records:
        source_records = [
            {"camera_id": camera_templates[i % len(camera_templates)], "frame_id": 10 + i * 5}
            for i in range(4)
        ]

    # Deduplicate observations by camera
    seen_cameras: set[str] = set()
    observations: List[Dict[str, Any]] = []

    for index, record in enumerate(source_records):
        camera_id = str(record.get("camera_id", camera_templates[index % len(camera_templates)]))
        if camera_id in seen_cameras:
            continue
        seen_cameras.add(camera_id)

        frame_id = int(record.get("frame_id", index + 1))
        if "captured_at" in record:
            captured_at_str = record["captured_at"]
        else:
            offset = {"c020": 25.905, "c023": 45.716, "c029": 125.788, "c035": 165.568}.get(camera_id, 0.0)
            ts = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=offset + frame_id / 10.0)
            captured_at_str = ts.isoformat()

        obs_plate = record.get("fused_plate_text") or plate_text
        obs_conf = float(record.get("fused_confidence", 0.92))
        obs_type = record.get("vehicle_type", "car")
        obs_colour = record.get("vehicle_colour", "white")

        rel_profile = profiles.get(camera_id, {})
        cam_reliability = select_reliability(rel_profile, captured_at_str)

        observations.append({
            "camera_id": camera_id,
            "camera_name": record.get("camera_name") or f"Camera {camera_id.upper()}",
            "captured_at": captured_at_str,
            "fused_plate_text": obs_plate,
            "fused_confidence": obs_conf,
            "vehicle_type": obs_type,
            "vehicle_colour": obs_colour,
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
            # Evidence fields — populated below from cross-camera pair scoring
            "plate_similarity": None,
            "ocr_confidence_component": None,
            "appearance_similarity": None,
            "temporal_score": None,
            "camera_transition_score": None,
            "attribute_match": None,
            "camera_reliability_weight": cam_reliability,
            "identity_score": None,
            "match_confidence_label": "candidate",
            "is_impossible_journey": False,
        })

    # Score cross-camera pairs
    pairs = pair_observations(observations, camera_profiles=profiles, road_graph=road_graph)
    best_evidence: Dict[int, Dict[str, Any]] = {}

    for pair in pairs:
        for idx in (pair["obs_index_a"], pair["obs_index_b"]):
            if idx not in best_evidence or pair["identity_score"] > best_evidence[idx]["identity_score"]:
                best_evidence[idx] = pair

    for idx, obs in enumerate(observations):
        ev = best_evidence.get(idx)
        if ev:
            obs["plate_similarity"] = ev.get("plate_similarity")
            obs["ocr_confidence_component"] = ev.get("ocr_confidence_component")
            obs["appearance_similarity"] = ev.get("appearance_similarity")
            obs["temporal_score"] = ev.get("temporal_score")
            obs["camera_transition_score"] = ev.get("camera_transition_score")
            obs["attribute_match"] = ev.get("attribute_match")
            obs["identity_score"] = ev["identity_score"]
            obs["match_confidence_label"] = ev["match_confidence_label"]

    return {"plate": plate_text, "observations": observations}


__all__ = [
    "CONFIRM_THRESHOLD",
    "CANDIDATE_THRESHOLD",
    "levenshtein_similarity",
    "select_reliability",
    "compute_identity_score",
    "compute_temporal_score",
    "compute_camera_transition_score",
    "pair_observations",
    "build_vehicle_trajectory",
    "load_camera_reliability_profiles",
    "match_observation_pair",
    "run_identity_fusion_on_database",
    "_update_canonical_vehicles",
]
