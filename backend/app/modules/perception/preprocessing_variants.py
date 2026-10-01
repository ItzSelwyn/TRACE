"""Layer 1 — Perception Module: Controlled License Plate Preprocessing Variants."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("trace.perception.preprocessing_variants")


def perspective_deskew(crop: np.ndarray) -> Optional[np.ndarray]:
    """Attempt safe quadrilateral perspective deskew if 4 distinct plate corners exist."""
    if crop is None or crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 50:
        return None
    try:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        h, w = crop.shape[:2]
        crop_area = h * w
        best_poly = None
        max_area = 0.0

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                # Plate contour must cover 40% to 95% of crop
                if 0.40 * crop_area <= area <= 0.95 * crop_area:
                    if area > max_area:
                        max_area = area
                        best_poly = approx

        if best_poly is None:
            return None

        pts = best_poly.reshape(4, 2).astype(np.float32)
        # Order points: top-left, top-right, bottom-right, bottom-left
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)

        rect = np.zeros((4, 2), dtype=np.float32)
        rect[0] = pts[np.argmin(s)]        # TL
        rect[2] = pts[np.argmax(s)]        # BR
        rect[1] = pts[np.argmin(diff)]     # TR
        rect[3] = pts[np.argmax(diff)]     # BL

        width_a = np.linalg.norm(rect[1] - rect[0])
        width_b = np.linalg.norm(rect[2] - rect[3])
        max_w = max(int(width_a), int(width_b), 120)

        height_a = np.linalg.norm(rect[3] - rect[0])
        height_b = np.linalg.norm(rect[2] - rect[1])
        max_h = max(int(height_a), int(height_b), 36)

        aspect = float(max_w) / max(1.0, float(max_h))
        if not (1.8 <= aspect <= 6.0):
            return None

        dst = np.array([
            [0, 0],
            [max_w - 1, 0],
            [max_w - 1, max_h - 1],
            [0, max_h - 1]
        ], dtype=np.float32)

        m = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(crop, m, (max_w, max_h), flags=cv2.INTER_CUBIC)
        return warped
    except Exception:
        return None


def generate_preprocessing_variants(
    crop: np.ndarray,
    target_height: int = 64,
    limit_variants: Optional[List[str]] = None,
) -> List[Tuple[str, np.ndarray]]:
    """Generate controlled, non-destructive preprocessing variants for OCR inference.
    
    Returns a list of (variant_name, image_ndarray).
    """
    if crop is None or crop.size == 0 or crop.shape[0] < 4 or crop.shape[1] < 4:
        return []

    variants: List[Tuple[str, np.ndarray]] = []
    h, w = crop.shape[:2]

    # Normalize base image size (maintain aspect ratio, scale to target height ~64px)
    scale = max(1.0, float(target_height) / max(1.0, float(h)))
    base_w = max(120, int(w * scale))
    base_h = max(target_height, int(h * scale))
    base = cv2.resize(crop, (base_w, base_h), interpolation=cv2.INTER_CUBIC)

    # 1. Original (standardized scale)
    variants.append(("ORIGINAL", base))

    # 2. 2x Upscale (crisp interpolation)
    up2 = cv2.resize(base, (int(base_w * 1.5), int(base_h * 1.5)), interpolation=cv2.INTER_CUBIC)
    variants.append(("UPSCALE_2X", up2))

    # 3. Grayscale (3-channel representation for PaddleOCR compatibility)
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY) if base.ndim == 3 else base
    gray_3ch = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    variants.append(("GRAYSCALE", gray_3ch))

    # 4. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    clahe_gray = clahe.apply(gray)
    clahe_3ch = cv2.cvtColor(clahe_gray, cv2.COLOR_GRAY2BGR)
    variants.append(("CLAHE", clahe_3ch))

    # 5. Denoised + Unsharp Mask Sharpening
    try:
        denoised = cv2.bilateralFilter(base, d=5, sigmaColor=50, sigmaSpace=50)
        gaussian = cv2.GaussianBlur(denoised, (0, 0), 2.0)
        sharpened = cv2.addWeighted(denoised, 1.6, gaussian, -0.6, 0)
        variants.append(("DENOISED_SHARPEN", sharpened))
    except Exception:
        pass

    # 6. Adaptive Thresholding (gentle, avoiding stroke artifacts)
    try:
        adapt_th = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
        )
        adapt_3ch = cv2.cvtColor(adapt_th, cv2.COLOR_GRAY2BGR)
        variants.append(("ADAPTIVE_THRESH", adapt_3ch))
    except Exception:
        pass

    # 7. Perspective Correction (if reliable)
    deskewed = perspective_deskew(crop)
    if deskewed is not None:
        deskewed_res = cv2.resize(deskewed, (base_w, base_h), interpolation=cv2.INTER_CUBIC)
        variants.append(("PERSPECTIVE_CORRECT", deskewed_res))

    if limit_variants:
        variants = [v for v in variants if v[0] in limit_variants]

    return variants
