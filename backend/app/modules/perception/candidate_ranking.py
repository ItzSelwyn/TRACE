"""Layer 1 — Perception Module: Plate Candidate Ranking and Crop Quality Assessment."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("trace.perception.candidate_ranking")


def laplacian_sharpness(img: np.ndarray) -> float:
    """Compute Laplacian variance metric to estimate image edge sharpness.
    
    Higher values indicate crisper edges. Values below ~40-50 indicate significant blur.
    """
    if img is None or img.size == 0:
        return 0.0
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        return 0.0


def motion_blur_score(img: np.ndarray) -> float:
    """Evaluate directional motion blur using Sobel gradient directional energy.
    
    Returns a score between 0.0 (heavily motion blurred) and 1.0 (sharp/isotropic gradients).
    """
    if img is None or img.size == 0 or img.shape[0] < 8 or img.shape[1] < 8:
        return 0.0
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)

        var_x = float(np.var(gx))
        var_y = float(np.var(gy))
        total_var = var_x + var_y

        if total_var < 1e-4:
            return 0.0

        # Anisotropy ratio: extreme differences between horizontal and vertical gradient indicate motion streaks
        ratio = min(var_x, var_y) / max(var_x, var_y, 1e-4)
        # Moderate sharpness multiplier
        norm_total = min(1.0, total_var / 800.0)
        return float(ratio * 0.5 + norm_total * 0.5)
    except Exception:
        return 0.5


def brightness_contrast_score(img: np.ndarray) -> float:
    """Score image exposure and dynamic contrast range.
    
    Optimal mean brightness is between 80 and 180 (scale 0-255).
    Standard deviation below 25 indicates washed out or completely dark plates.
    """
    if img is None or img.size == 0:
        return 0.0
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        mean_b = float(np.mean(gray))
        std_b = float(np.std(gray))

        # Contrast component: std_b >= 45 is ideal
        contrast_score = min(1.0, std_b / 45.0)

        # Brightness component: penalize < 40 or > 220
        if 80 <= mean_b <= 180:
            bright_score = 1.0
        elif mean_b < 80:
            bright_score = max(0.1, mean_b / 80.0)
        else:
            bright_score = max(0.1, (255.0 - mean_b) / 75.0)

        return float(contrast_score * 0.6 + bright_score * 0.4)
    except Exception:
        return 0.5


def dimension_score(crop: np.ndarray) -> float:
    """Evaluate crop geometry suitability for optical character recognition."""
    if crop is None or crop.size == 0:
        return 0.0
    h, w = crop.shape[:2]
    if h < 12 or w < 30:
        return 0.05

    aspect = float(w) / max(1.0, float(h))
    # Standard Indian rectangular plates have aspect ratio ~3.0 - 4.5; square/scooter plates ~1.8 - 2.5
    if 2.0 <= aspect <= 5.5:
        aspect_score = 1.0
    elif 1.4 <= aspect <= 6.5:
        aspect_score = 0.7
    else:
        aspect_score = 0.3

    # Resolution scaling: height >= 32px is ideal for PaddleOCR character detection
    res_score = min(1.0, h / 36.0) * min(1.0, w / 120.0)

    return float(aspect_score * 0.5 + res_score * 0.5)


def boundary_clipping_penalty(
    bbox: Optional[List[int]],
    frame_shape: Optional[Tuple[int, ...]],
    margin_px: int = 4,
) -> float:
    """Check whether the bounding box is clipped by frame boundaries.
    
    Returns a multiplier from 0.4 (severely clipped) to 1.0 (safely inside frame).
    """
    if not bbox or len(bbox) < 4 or not frame_shape or len(frame_shape) < 2:
        return 1.0
    fh, fw = frame_shape[:2]
    x1, y1, x2, y2 = bbox[:4]

    clipped = 0
    if x1 <= margin_px:
        clipped += 1
    if y1 <= margin_px:
        clipped += 1
    if x2 >= fw - margin_px:
        clipped += 1
    if y2 >= fh - margin_px:
        clipped += 1

    if clipped == 0:
        return 1.0
    elif clipped == 1:
        return 0.75
    else:
        return 0.40


def score_candidate_frame(
    crop: np.ndarray,
    bbox: Optional[List[int]] = None,
    frame_shape: Optional[Tuple[int, ...]] = None,
    det_conf: float = 1.0,
) -> Dict[str, Any]:
    """Combine all visual quality metrics into a single unified candidate ranking score.
    
    Returns a dictionary with metric components and overall composite score [0.0, 1.0].
    """
    if crop is None or crop.size == 0:
        return {
            "composite_score": 0.0,
            "sharpness": 0.0,
            "motion_blur": 0.0,
            "brightness_contrast": 0.0,
            "dimension": 0.0,
            "clip_penalty": 0.0,
            "is_promising": False,
        }

    raw_sharp = laplacian_sharpness(crop)
    sharp_score = min(1.0, raw_sharp / 150.0)
    motion_sc = motion_blur_score(crop)
    bc_sc = brightness_contrast_score(crop)
    dim_sc = dimension_score(crop)
    clip_pen = boundary_clipping_penalty(bbox, frame_shape)
    norm_det_conf = min(1.0, max(0.1, det_conf))

    composite = (
        sharp_score * 0.35
        + motion_sc * 0.20
        + bc_sc * 0.20
        + dim_sc * 0.15
        + norm_det_conf * 0.10
    ) * clip_pen

    composite = round(float(np.clip(composite, 0.0, 1.0)), 4)
    # A candidate is promising for expensive OCR if composite >= 0.25 and height >= 14
    is_promising = bool(composite >= 0.25 and crop.shape[0] >= 14 and crop.shape[1] >= 40)

    return {
        "composite_score": composite,
        "sharpness": round(raw_sharp, 2),
        "motion_blur": round(motion_sc, 3),
        "brightness_contrast": round(bc_sc, 3),
        "dimension": round(dim_sc, 3),
        "clip_penalty": round(clip_pen, 2),
        "is_promising": is_promising,
    }
