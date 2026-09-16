"""Layer 1 — Perception Module: Robust PaddleOCR engine with graceful error containment."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from app.modules.perception.normalization import is_valid_indian_plate, normalize_plate_text

logger = logging.getLogger("trace.perception.ocr")

_OCR_INSTANCE: Optional[Any] = None
_OCR_LOCK = threading.Lock()
_OCR_INITIALIZED = False


def enhance_plate_contrast(img: np.ndarray) -> np.ndarray:
    """Apply CLAHE on the L-channel of LAB color space to equalize local contrast."""
    if img is None or img.size == 0:
        return img
    try:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    except Exception:
        return img


def unsharp_mask(img: np.ndarray, sigma: float = 1.2, strength: float = 1.4) -> np.ndarray:
    """Sharpen edges of blurry characters using unsharp masking."""
    if img is None or img.size == 0:
        return img
    try:
        blurred = cv2.GaussianBlur(img, (0, 0), sigma)
        sharpened = cv2.addWeighted(img, 1.0 + strength, blurred, -strength, 0)
        return np.clip(sharpened, 0, 255).astype(np.uint8)
    except Exception:
        return img


def super_resolve_plate(img: np.ndarray, min_height: int = 80, min_width: int = 240) -> np.ndarray:
    """Adaptively upscale low-resolution plate crops to optimal character reading scale."""
    if img is None or img.size == 0:
        return img
    h, w = img.shape[:2]
    if h >= min_height and w >= min_width:
        return img
    scale = max(min_height / max(1, h), min_width / max(1, w))
    scale = min(scale, 4.0)  # Capped to 4x to avoid excessive digital artifacts
    target_w = int(w * scale)
    target_h = int(h * scale)
    return cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_CUBIC)


def normalize_plate_illumination(img: np.ndarray) -> np.ndarray:
    """Remove uneven shadows and boost character stroke contrast using Top-Hat / Black-Hat morphology."""
    if img is None or img.size == 0:
        return img
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, rect_kernel)
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kernel)
        contrast = cv2.add(gray, tophat)
        contrast = cv2.subtract(contrast, blackhat)
        return cv2.cvtColor(contrast, cv2.COLOR_GRAY2BGR)
    except Exception:
        return img


def get_ocr_engine() -> Optional[Any]:
    """Thread-safe singleton getter for PaddleOCR with tuned low-light/faint text detection parameters."""
    global _OCR_INSTANCE, _OCR_INITIALIZED
    with _OCR_LOCK:
        if not _OCR_INITIALIZED:
            _OCR_INITIALIZED = True
            try:
                import logging as _py_logging
                import os
                os.environ["FLAGS_use_mkldnn"] = "0"
                os.environ["FLAGS_use_onednn"] = "0"
                _py_logging.getLogger("ppocr").setLevel(_py_logging.ERROR)

                from paddleocr import PaddleOCR
                _OCR_INSTANCE = PaddleOCR(
                    use_angle_cls=False,
                    lang="en",
                    enable_mkldnn=False,
                    use_gpu=False,
                    show_log=False,
                    det_db_thresh=0.20,       # Lower threshold to detect faint/low-contrast characters
                    det_db_box_thresh=0.40,   # Lower box score threshold for blurry plates
                    det_db_unclip_ratio=2.0,  # Expand bounding box slightly to capture edge letters
                    use_dilation=True,        # Dilate text features to connect segmented character strokes
                    det_limit_side_len=960,   # High-resolution detection limit
                )
                logger.info("PaddleOCR engine initialized successfully with enhanced ANPR sensitivity.")
            except Exception as e:
                logger.warning(f"PaddleOCR failed to initialize: {e}")
                _OCR_INSTANCE = None
        return _OCR_INSTANCE


def read_plate_image(
    image_input: Union[str, Path, np.ndarray],
    min_confidence: float = 0.15,
    enable_enhancement: bool = True,
) -> List[Dict[str, Any]]:
    """Run PaddleOCR on an image path or numpy crop with multi-pass low-quality enhancement.
    
    Returns a list of dicts:
    [
        {
            "raw_text": str,
            "normalized_text": str,
            "confidence": float,
            "bbox": list, # [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        }
    ]
    """
    ocr = get_ocr_engine()
    if ocr is None:
        return []

    try:
        if isinstance(image_input, (str, Path)):
            img_path = str(image_input)
            if not Path(img_path).exists():
                logger.warning(f"[OCR WARNING] Image file not found: {img_path}")
                return []
            img_mat = cv2.imread(img_path)
            if img_mat is None:
                return []
        elif isinstance(image_input, np.ndarray):
            if image_input.size == 0 or image_input.shape[0] < 5 or image_input.shape[1] < 5:
                return []
            img_mat = image_input
        else:
            return []

        def _run_single_pass(mat: np.ndarray) -> List[Dict[str, Any]]:
            try:
                res = ocr.ocr(mat, cls=False)
            except Exception:
                return []
            if not res or not res[0]:
                return []
            lines = []
            for item in res[0]:
                if not item or len(item) < 2:
                    continue
                box, (txt, score) = item
                conf = float(score) if score is not None else 0.0
                if conf < min_confidence:
                    continue
                raw = str(txt).strip()
                norm = normalize_plate_text(raw)
                if not norm:
                    continue
                lines.append({
                    "raw_text": raw,
                    "normalized_text": norm,
                    "confidence": round(conf, 4),
                    "bbox": box,
                })
            return lines

        # Pass 1: Standard input
        pass1_results = _run_single_pass(img_mat)

        # Fast exit if Pass 1 already found a confident, valid Indian plate
        if pass1_results and any(is_valid_indian_plate(r["normalized_text"]) and r["confidence"] >= 0.82 for r in pass1_results):
            return pass1_results

        if not enable_enhancement:
            return pass1_results

        # Pass 2 (Enhancement for low-quality / blurry / low-contrast footage):
        # Super-resolution upscaling + edge sharpening + LAB CLAHE
        enhanced = enhance_plate_contrast(unsharp_mask(super_resolve_plate(img_mat)))
        pass2_results = _run_single_pass(enhanced)

        # Pass 3 (Illumination normalization for uneven shadows / glare):
        # Run only if still no valid candidate
        pass3_results: List[Dict[str, Any]] = []
        has_valid_so_far = any(
            is_valid_indian_plate(r["normalized_text"])
            for r in (pass1_results + pass2_results)
        )
        if not has_valid_so_far:
            norm_illum = normalize_plate_illumination(enhanced)
            pass3_results = _run_single_pass(norm_illum)

        # Merge and deduplicate results, keeping highest confidence read for each unique normalized text
        all_reads = pass1_results + pass2_results + pass3_results
        best_by_text: Dict[str, Dict[str, Any]] = {}
        for r in all_reads:
            nt = r["normalized_text"]
            if nt not in best_by_text or r["confidence"] > best_by_text[nt]["confidence"]:
                best_by_text[nt] = r

        return list(best_by_text.values())

    except Exception as e:
        logger.warning(f"[OCR WARNING] PaddleOCR inference error: {e}")
        return []

