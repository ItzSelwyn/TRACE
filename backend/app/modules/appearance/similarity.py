"""Cosine Similarity and Calibration for Vehicle Re-ID Embeddings."""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Union

import numpy as np

from app.config import settings

logger = logging.getLogger("trace.appearance.similarity")


def compute_cosine_similarity(
    emb_a: Optional[Union[Sequence[float], np.ndarray]],
    emb_b: Optional[Union[Sequence[float], np.ndarray]],
) -> Optional[float]:
    """Compute raw cosine similarity between two L2-normalized embedding vectors.

    Returns:
        float in [-1.0, 1.0], or None if either vector is missing or invalid.
    """
    if emb_a is None or emb_b is None:
        return None

    try:
        a = np.asarray(emb_a, dtype=np.float32)
        b = np.asarray(emb_b, dtype=np.float32)

        if a.size == 0 or b.size == 0 or a.shape != b.shape:
            return None

        if not np.isfinite(a).all() or not np.isfinite(b).all():
            return None

        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))

        if norm_a <= 1e-7 or norm_b <= 1e-7:
            return None

        # Compute dot product normalized by lengths
        dot = float(np.dot(a, b) / (norm_a * norm_b))
        return round(float(np.clip(dot, -1.0, 1.0)), 4)
    except Exception as e:
        logger.debug(f"Error computing cosine similarity: {e}")
        return None


def compute_calibrated_similarity(
    cosine: float,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> float:
    """Map raw cosine similarity to identity similarity in [0.0, 1.0] expected by Layer 2.

    The calibration thresholds are derived empirically from CityFlowV2 validation:
    - Cosine values <= min_val map to 0.0 (completely dissimilar vehicles).
    - Cosine values >= max_val map to 1.0 (very high confidence visual match).
    - Values in between scale linearly.

    Args:
        cosine: Raw cosine similarity in [-1.0, 1.0].
        min_val: Lower baseline bound (defaults to settings.APPEARANCE_COSINE_MIN).
        max_val: Upper confirmation bound (defaults to settings.APPEARANCE_COSINE_MAX).

    Returns:
        Calibrated appearance similarity float in [0.0, 1.0].
    """
    lo = min_val if min_val is not None else settings.APPEARANCE_COSINE_MIN
    hi = max_val if max_val is not None else settings.APPEARANCE_COSINE_MAX

    if hi <= lo:
        return 1.0 if cosine >= hi else 0.0

    scaled = (cosine - lo) / (hi - lo)
    return round(float(np.clip(scaled, 0.0, 1.0)), 4)


def compute_appearance_similarity(
    emb_a: Optional[Union[Sequence[float], np.ndarray]],
    emb_b: Optional[Union[Sequence[float], np.ndarray]],
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> Optional[float]:
    """End-to-end appearance similarity between two vehicle embeddings.

    Returns:
        Calibrated float in [0.0, 1.0], or None if either embedding is absent.
    """
    raw_cosine = compute_cosine_similarity(emb_a, emb_b)
    if raw_cosine is None:
        return None
    return compute_calibrated_similarity(raw_cosine, min_val=min_val, max_val=max_val)
