"""Layer 2 — Identity Fusion Module: Exact Multimodal Identity Scoring & Explainable Evidence."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

from app.config import settings

logger = logging.getLogger("trace.identity.scoring")

# Locked-down weights from TRACE Agent Build Brief §2.1 & M3 Specifications
WEIGHT_PLATE_SIMILARITY: float = 0.50
WEIGHT_OCR_CONFIDENCE: float = 0.30
WEIGHT_TYPE_MATCH: float = 0.10
WEIGHT_COLOUR_MATCH: float = 0.10

# Thresholds from settings / Agent Build Brief
CONFIRM_THRESHOLD: float = getattr(settings, "IDENTITY_CONFIRM_THRESHOLD", 0.70)
CANDIDATE_THRESHOLD: float = getattr(settings, "IDENTITY_CANDIDATE_THRESHOLD", 0.40)


def levenshtein_similarity(a: str | None, b: str | None) -> float:
    """Return normalized Levenshtein similarity in [0.0, 1.0].
    
    Formula: similarity = 1 - (edit_distance / max(len(a), len(b)))
    
    Edge cases:
    - Identical non-empty or empty strings -> 1.0
    - One empty, other non-empty -> 0.0
    - Safe against division by zero
    """
    s1 = str(a or "").upper().strip()
    s2 = str(b or "").upper().strip()

    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0

    # Dynamic programming Levenshtein distance
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
    sim = max(0.0, 1.0 - (dist / max_len))
    return round(sim, 4)


def _is_daytime(captured_at: Union[str, datetime]) -> bool:
    """Return True if observation was captured during daytime (06:00–18:00)."""
    if isinstance(captured_at, str):
        try:
            dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            return 6 <= dt.hour < 18
        except Exception:
            return True
    elif isinstance(captured_at, datetime):
        return 6 <= captured_at.hour < 18
    return True


def select_reliability(profile: Optional[Dict[str, Any]], captured_at: Union[str, datetime]) -> float:
    """Select the applicable camera OCR reliability factor based on condition / time of day."""
    if not profile:
        return 0.85  # Safe default reliability

    # Check daytime vs nighttime
    if _is_daytime(captured_at):
        return float(profile.get("day_ocr_reliability", 0.90))
    return float(profile.get("night_ocr_reliability", 0.75))


def compute_identity_score(
    obs_a: Dict[str, Any],
    obs_b: Dict[str, Any],
    camera_profile_a: Optional[Dict[str, Any]] = None,
    camera_profile_b: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute the multi-modal identity score between two vehicle observations.
    
    Formula:
        identity_score = 0.5 * plate_similarity
                       + 0.3 * ocr_confidence_component
                       + 0.1 * type_match
                       + 0.1 * colour_match
    
    Returns structured explainable evidence breakdown.
    """
    plate_a = str(obs_a.get("fused_plate_text") or obs_a.get("plate") or "").strip()
    plate_b = str(obs_b.get("fused_plate_text") or obs_b.get("plate") or "").strip()

    # If plate is unreadable on either, treat similarity as 0.0
    if plate_a.upper() in ["NOT READ", "UNREADABLE", ""] or plate_b.upper() in ["NOT READ", "UNREADABLE", ""]:
        plate_sim = 0.0
    else:
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
    ocr_conf_comp = round((eff_conf_a + eff_conf_b) / 2.0, 4)
    cam_rel_weight = round((rel_a + rel_b) / 2.0, 4)

    # Vehicle type match (1 if match, 0 otherwise)
    type_a = str(obs_a.get("vehicle_type", "")).lower().strip()
    type_b = str(obs_b.get("vehicle_type", "")).lower().strip()
    type_match_bool = bool(type_a and type_b and type_a == type_b)
    type_match_val = 1.0 if type_match_bool else 0.0

    # Vehicle colour match (1 if match, 0 otherwise)
    col_a = str(obs_a.get("vehicle_colour") or obs_a.get("color") or "").lower().strip()
    col_b = str(obs_b.get("vehicle_colour") or obs_b.get("color") or "").lower().strip()
    colour_match_bool = bool(col_a and col_b and col_a == col_b)
    colour_match_val = 1.0 if colour_match_bool else 0.0

    # Composite Identity Score
    score = round(
        WEIGHT_PLATE_SIMILARITY * plate_sim
        + WEIGHT_OCR_CONFIDENCE * ocr_conf_comp
        + WEIGHT_TYPE_MATCH * type_match_val
        + WEIGHT_COLOUR_MATCH * colour_match_val,
        4,
    )
    score = min(max(score, 0.0), 1.0)

    # Status classification
    if score >= CONFIRM_THRESHOLD:
        status = "CONFIRMED"
        label = "confirmed"
    elif score >= CANDIDATE_THRESHOLD:
        status = "LOW_CONFIDENCE"
        label = "candidate"
    else:
        status = "NO_MATCH"
        label = "no_match"

    # Attribute match score for UI evidence panel (0.5 type + 0.5 colour)
    attr_match_score = round(0.5 * type_match_val + 0.5 * colour_match_val, 4)

    return {
        "plate_a": plate_a,
        "plate_b": plate_b,
        "plate_similarity": plate_sim,
        "raw_ocr_confidence_a": raw_conf_a,
        "raw_ocr_confidence_b": raw_conf_b,
        "reliability_a": rel_a,
        "reliability_b": rel_b,
        "ocr_confidence_component": ocr_conf_comp,
        "camera_reliability_weight": cam_rel_weight,
        "type_match": type_match_bool,
        "colour_match": colour_match_bool,
        "attribute_match": attr_match_score,
        "identity_score": score,
        "status": status,
        "match_confidence_label": label,
    }
