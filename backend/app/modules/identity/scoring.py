"""Layer 2 — Identity Fusion Module: Multi-Modal Identity Scoring Engine.

Supports two modes selected automatically based on available evidence:

CityFlowV2 / visual-only mode (default, no plate required):
    appearance_similarity  55%
    temporal_score         25%
    camera_transition      15%
    colour_score            3%
    type_score              2%

ANPR-capable mode (activated when both observations have readable plates):
    plate_similarity       35%
    appearance_similarity  30%
    temporal_score         15%
    camera_transition      10%
    colour_score            5%
    type_score              5%

Weight redistribution:
    When any modality is unavailable (None), its configured weight is
    proportionally redistributed among the available modalities so the
    composite score stays in [0, 1] regardless of which sensors are present.
    Unavailable != evidence of mismatch.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from app.config import settings

logger = logging.getLogger("trace.identity.scoring")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
CONFIRM_THRESHOLD: float = settings.IDENTITY_CONFIRM_THRESHOLD
CANDIDATE_THRESHOLD: float = settings.IDENTITY_CANDIDATE_THRESHOLD

# Sentinel values treated as "plate unavailable"
_UNREADABLE_PLATES = {"NOT READ", "UNREADABLE", "", "NONE", "N/A"}


def _is_plate_unavailable(text: Optional[str]) -> bool:
    """Return True if the plate text represents an unreadable / unavailable plate."""
    if text is None:
        return True
    return str(text).upper().strip() in _UNREADABLE_PLATES


def levenshtein_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Normalized Levenshtein similarity in [0.0, 1.0].

    Formula: similarity = 1 - (edit_distance / max(len(a), len(b)))
    Edge cases:
    - Identical strings   -> 1.0
    - Both empty          -> 1.0
    - One empty, other not -> 0.0
    """
    s1 = str(a or "").upper().strip()
    s2 = str(b or "").upper().strip()

    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    max_len = max(len(s1), len(s2))

    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    dist = dp[m][n]
    return round(max(0.0, 1.0 - (dist / max_len)), 4)


def _is_daytime(captured_at: Union[str, datetime, None]) -> bool:
    """Return True if observation was captured during daytime (06:00–18:00 UTC)."""
    if captured_at is None:
        return True
    if isinstance(captured_at, str):
        try:
            dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            return 6 <= dt.hour < 18
        except Exception:
            return True
    elif isinstance(captured_at, datetime):
        return 6 <= captured_at.hour < 18
    return True


def select_reliability(
    profile: Optional[Dict[str, Any]],
    captured_at: Union[str, datetime, None],
) -> float:
    """Return applicable camera OCR reliability factor based on time of day."""
    if not profile:
        return 0.85
    if _is_daytime(captured_at):
        return float(profile.get("day_ocr_reliability", 0.90))
    return float(profile.get("night_ocr_reliability", 0.75))


_CAMERA_ALIAS_TO_ID: Dict[str, str] = {
    "c020": "c1000000-0000-0000-0000-000000000001",
    "c023": "c2000000-0000-0000-0000-000000000002",
    "c029": "c3000000-0000-0000-0000-000000000003",
    "c035": "c4000000-0000-0000-0000-000000000004",
    "cam-13": "c1000000-0000-0000-0000-000000000001",
    "cam-14": "c2000000-0000-0000-0000-000000000002",
    "cam-15": "c3000000-0000-0000-0000-000000000003",
    "cam-16": "c4000000-0000-0000-0000-000000000004",
}


def _normalize_camera_id(cid: Optional[str]) -> Optional[str]:
    """Normalize short alias (e.g. c020) to canonical UUID string for road-graph lookups."""
    if not cid:
        return None
    clean = str(cid).lower().strip()
    return _CAMERA_ALIAS_TO_ID.get(clean, clean)


def compute_temporal_score(
    time_gap_s: Optional[float],
    from_camera_id: Optional[str],
    to_camera_id: Optional[str],
    road_graph: Optional[Dict[str, Any]] = None,
) -> float:
    """Score temporal plausibility of a cross-camera observation pair in [0, 1].

    Returns:
        0.0  — impossible journey (time_gap_s < min_travel_time_s, or negative)
        0.5  — no path found in graph (unknown relationship, partial credit)
        1.0  — reachable within min..max_travel_time window
        0.85 — reachable but beyond max_travel_time (possible detour/slow)
    Returns 1.0 when camera IDs are unavailable (cannot penalise).
    """
    from_id = _normalize_camera_id(from_camera_id)
    to_id = _normalize_camera_id(to_camera_id)

    if from_id is None or to_id is None:
        return 1.0  # cannot evaluate — give benefit of the doubt

    if from_id == to_id:
        # Same camera re-sighting, always temporally consistent
        return 1.0

    if time_gap_s is None:
        return 1.0  # timestamps unavailable

    if time_gap_s < 0:
        # Observation B precedes Observation A — physically impossible
        return 0.0

    try:
        from app.modules.spatial_temporal import reachability_check
        from app.modules.spatial_temporal.road_graph import get_road_graph

        g = road_graph or get_road_graph()
        reach = reachability_check(from_id, to_id, time_gap_s, g)

        if reach["min_travel_time_s"] is None:
            # No path in graph — unknown camera relationship
            return 0.5

        if not reach["reachable"]:
            # time_gap_s < min_travel_time_s — impossible
            return 0.0

        # Check if within max_travel_time for a well-defined score
        adj = g.get("adj", {})
        max_travel_time_s = None
        for edge in adj.get(from_id, []):
            if edge["to_camera_id"] == to_id:
                max_travel_time_s = edge.get("max_travel_time_s")
                break

        if max_travel_time_s is not None and time_gap_s > max_travel_time_s:
            return 0.85  # reachable but took longer than expected

        return 1.0

    except Exception:
        return 1.0  # graph unavailable — cannot penalise


def compute_camera_transition_score(
    from_camera_id: Optional[str],
    to_camera_id: Optional[str],
    road_graph: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """Score how plausible a camera-to-camera transition is in [0, 1] or None.

    Returns:
        None — same camera (not applicable; caller should omit this signal)
        1.0  — direct road edge exists between the two cameras
        0.7  — reachable via intermediate cameras (multi-hop)
        0.3  — no path found (unknown topology — some credit, not zero)
    """
    from_id = _normalize_camera_id(from_camera_id)
    to_id = _normalize_camera_id(to_camera_id)

    if from_id is None or to_id is None:
        return None

    if from_id == to_id:
        return None  # same camera — not applicable

    try:
        from app.modules.spatial_temporal.road_graph import get_road_graph
        from app.modules.spatial_temporal import shortest_path

        g = road_graph or get_road_graph()
        adj = g.get("adj", {})

        # Check for direct edge
        for edge in adj.get(from_id, []):
            if edge["to_camera_id"] == to_id:
                return 1.0

        # Check for multi-hop path
        min_time, path = shortest_path(g, from_id, to_id)
        if min_time < float("inf") and len(path) > 1:
            return 0.7

        # No path known
        return 0.3

    except Exception:
        return None  # graph unavailable — omit the signal


def _weighted_score(
    components: List[Tuple[str, Optional[float], float]],
) -> Tuple[float, Dict[str, Any]]:
    """Compute a weighted sum with proportional weight redistribution for unavailable components.

    Args:
        components: list of (name, value_or_None, configured_weight)

    Returns:
        (composite_score, debug_dict)
    """
    available = [(name, val, w) for name, val, w in components if val is not None]
    total_available_weight = sum(w for _, _, w in available)

    if not available or total_available_weight == 0.0:
        return 0.0, {"error": "no_components_available"}

    score = 0.0
    debug: Dict[str, Any] = {}
    for name, val, w in available:
        effective_w = w / total_available_weight
        contribution = effective_w * val
        score += contribution
        debug[name] = {"value": round(val, 4), "configured_weight": round(w, 4), "effective_weight": round(effective_w, 4)}

    return round(min(max(score, 0.0), 1.0), 4), debug


def compute_identity_score(
    obs_a: Dict[str, Any],
    obs_b: Dict[str, Any],
    camera_profile_a: Optional[Dict[str, Any]] = None,
    camera_profile_b: Optional[Dict[str, Any]] = None,
    appearance_similarity: Optional[float] = None,
    camera_id_a: Optional[str] = None,
    camera_id_b: Optional[str] = None,
    time_gap_s: Optional[float] = None,
    road_graph: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute multi-modal identity score between two vehicle observations.

    Mode is selected automatically:
    - ANPR mode: both plates are readable -> plate evidence contributes strongly
    - CityFlowV2 mode: one or both plates unavailable -> visual/temporal primary

    Unavailable modalities have their weight redistributed rather than being
    treated as evidence of mismatch.

    Args:
        obs_a / obs_b:        dicts with fused_plate_text, fused_confidence,
                               vehicle_type, vehicle_colour, captured_at
        camera_profile_a/b:   camera reliability dicts (day/night reliability)
        appearance_similarity: cosine/Reid similarity float in [0,1], or None
        camera_id_a/b:        string camera IDs for road-graph lookup
        time_gap_s:           pre-computed seconds between captured_at timestamps
        road_graph:           pre-loaded road graph dict (loaded lazily if None)

    Returns:
        Dict with identity_score, status, all component values, evidence dict.
    """
    # --- Extract plate texts ---
    plate_a = str(obs_a.get("fused_plate_text") or obs_a.get("plate") or "").strip()
    plate_b = str(obs_b.get("fused_plate_text") or obs_b.get("plate") or "").strip()
    plates_unavailable_a = _is_plate_unavailable(plate_a)
    plates_unavailable_b = _is_plate_unavailable(plate_b)
    both_plates_available = not plates_unavailable_a and not plates_unavailable_b

    # --- Camera IDs for temporal / transition scoring ---
    cam_a = camera_id_a or obs_a.get("camera_id") or obs_a.get("cam_id")
    cam_b = camera_id_b or obs_b.get("camera_id") or obs_b.get("cam_id")
    # Ensure they are strings
    cam_a = str(cam_a) if cam_a else None
    cam_b = str(cam_b) if cam_b else None

    # --- Time gap (compute from captured_at if not pre-computed) ---
    if time_gap_s is None:
        try:
            raw_a = obs_a.get("captured_at") or obs_a.get("timestamp")
            raw_b = obs_b.get("captured_at") or obs_b.get("timestamp")
            if raw_a and raw_b:
                def _parse(ts: Any) -> datetime:
                    if isinstance(ts, datetime):
                        return ts
                    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                ts_a = _parse(raw_a)
                ts_b = _parse(raw_b)
                time_gap_s = (ts_b - ts_a).total_seconds()
        except Exception:
            time_gap_s = None

    # --- Mode selection ---
    if both_plates_available:
        # ANPR-capable mode
        w_plate = settings.IDENTITY_PLATE_WEIGHT
        w_appearance = settings.IDENTITY_APPEARANCE_WEIGHT_ANPR
        w_temporal = settings.IDENTITY_TEMPORAL_WEIGHT_ANPR
        w_cam_transition = settings.IDENTITY_CAMERA_TRANSITION_WEIGHT_ANPR
        w_colour = settings.IDENTITY_COLOUR_WEIGHT_ANPR
        w_type = settings.IDENTITY_TYPE_WEIGHT_ANPR
        mode = "ANPR"
    else:
        # CityFlowV2 / visual-only mode
        w_plate = 0.0  # plate weight is 0 since unavailable
        w_appearance = settings.IDENTITY_APPEARANCE_WEIGHT
        w_temporal = settings.IDENTITY_TEMPORAL_WEIGHT
        w_cam_transition = settings.IDENTITY_CAMERA_TRANSITION_WEIGHT
        w_colour = settings.IDENTITY_COLOUR_WEIGHT
        w_type = settings.IDENTITY_TYPE_WEIGHT
        mode = "CITYFLOW"

    # --- 1. Plate similarity (only when both plates available) ---
    plate_sim: Optional[float] = None
    ocr_comp: Optional[float] = None
    if both_plates_available:
        plate_sim = levenshtein_similarity(plate_a, plate_b)
        # OCR confidence component with camera reliability weighting
        raw_conf_a = float(obs_a.get("fused_confidence") or obs_a.get("ocr_confidence") or 0.0)
        raw_conf_b = float(obs_b.get("fused_confidence") or obs_b.get("ocr_confidence") or 0.0)
        cap_a = obs_a.get("captured_at") or obs_a.get("timestamp") or ""
        cap_b = obs_b.get("captured_at") or obs_b.get("timestamp") or ""
        rel_a = select_reliability(camera_profile_a, cap_a)
        rel_b = select_reliability(camera_profile_b, cap_b)
        eff_conf_a = raw_conf_a * rel_a
        eff_conf_b = raw_conf_b * rel_b
        ocr_comp = round((eff_conf_a + eff_conf_b) / 2.0, 4)
    else:
        rel_a = select_reliability(camera_profile_a, obs_a.get("captured_at"))
        rel_b = select_reliability(camera_profile_b, obs_b.get("captured_at"))

    # --- 2. Appearance similarity (passed in from re-ID pipeline or None) ---
    # None = pipeline not present; weight redistributed

    # --- 3. Temporal score ---
    temporal = compute_temporal_score(time_gap_s, cam_a, cam_b, road_graph)

    # --- 4. Camera transition score ---
    cam_transition = compute_camera_transition_score(cam_a, cam_b, road_graph)

    # --- 5. Vehicle type score (soft: mismatch = 0.4, not 0.0) ---
    type_a = str(obs_a.get("vehicle_type", "") or "").lower().strip()
    type_b = str(obs_b.get("vehicle_type", "") or "").lower().strip()
    if type_a and type_b:
        type_score: Optional[float] = 1.0 if type_a == type_b else 0.4
    else:
        type_score = None  # unknown — omit from scoring

    # --- 6. Vehicle colour score (soft: mismatch = 0.3, not 0.0) ---
    col_a = str(obs_a.get("vehicle_colour") or obs_a.get("color") or "").lower().strip()
    col_b = str(obs_b.get("vehicle_colour") or obs_b.get("color") or "").lower().strip()
    if col_a and col_b:
        colour_score: Optional[float] = 1.0 if col_a == col_b else 0.3
    else:
        colour_score = None  # unknown — omit from scoring

    # --- Build component list for weighted scoring ---
    # In ANPR mode: plate and OCR are combined as a single "plate" component
    components: List[Tuple[str, Optional[float], float]] = []

    if mode == "ANPR":
        # Plate evidence is gated by plate similarity — OCR confidence validates
        # the read accuracy, it never rewards completely dissimilar plate text.
        if plate_sim is not None and ocr_comp is not None:
            plate_evidence = round(plate_sim * (0.25 + 0.75 * ocr_comp), 4)
            components.append(("plate", plate_evidence, w_plate))

    components.extend([
        ("appearance", appearance_similarity, w_appearance),
        ("temporal", temporal, w_temporal),
        ("camera_transition", cam_transition, w_cam_transition),
        ("colour", colour_score, w_colour),
        ("type", type_score, w_type),
    ])

    # --- Check for primary identity evidence ---
    has_primary_evidence = (
        (plate_sim is not None and mode == "ANPR") or
        (appearance_similarity is not None)
    )

    if not has_primary_evidence:
        # Safety guard against false positives (Requirement 15):
        # If BOTH license plate and visual appearance are absent, weak supporting evidence
        # (colour, type, temporal) alone CANNOT confirm vehicle identity.
        # Primary weights are NOT redistributed to weak attributes.
        raw_secondary = (
            w_temporal * (temporal or 0.0) +
            (w_cam_transition * cam_transition if cam_transition is not None else 0.0) +
            (w_colour * colour_score if colour_score is not None else 0.0) +
            (w_type * type_score if type_score is not None else 0.0)
        )
        score = round(min(raw_secondary, CANDIDATE_THRESHOLD - 0.01), 4)
        weight_debug = {
            "primary_evidence_missing": True,
            "raw_secondary_score": raw_secondary,
            "capped_score": score,
        }
    else:
        score, weight_debug = _weighted_score(components)

    # --- Status classification ---
    if score >= CONFIRM_THRESHOLD:
        status = "CONFIRMED"
        label = "confirmed"
    elif score >= CANDIDATE_THRESHOLD:
        status = "LOW_CONFIDENCE"
        label = "candidate"
    else:
        status = "NO_MATCH"
        label = "no_match"

    # --- Attribute match score for UI evidence panel ---
    type_match_bool = (type_a == type_b) if (type_a and type_b) else None
    colour_match_bool = (col_a == col_b) if (col_a and col_b) else None
    attr_match_score = None
    if type_match_bool is not None and colour_match_bool is not None:
        attr_match_score = round(0.5 * float(type_match_bool) + 0.5 * float(colour_match_bool), 4)

    return {
        # Core output
        "identity_score": score,
        "status": status,
        "match_confidence_label": label,
        "mode": mode,
        # Plate evidence (None when unavailable)
        "plate_a": plate_a if not plates_unavailable_a else None,
        "plate_b": plate_b if not plates_unavailable_b else None,
        "plate_similarity": plate_sim,
        "ocr_confidence_component": ocr_comp,
        "reliability_a": rel_a if both_plates_available else None,
        "reliability_b": rel_b if both_plates_available else None,
        # Visual / re-ID evidence
        "appearance_similarity": appearance_similarity,
        # Temporal / spatial evidence
        "temporal_score": temporal,
        "camera_transition_score": cam_transition,
        "time_gap_s": time_gap_s,
        # Attribute evidence
        "type_match": type_match_bool,
        "colour_match": colour_match_bool,
        "type_score": type_score,
        "colour_score": colour_score,
        "attribute_match": attr_match_score,
        # Explainability
        "weight_debug": weight_debug,
        "camera_reliability_weight": (
            round((rel_a + rel_b) / 2.0, 4) if both_plates_available else None
        ),
    }
