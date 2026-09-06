"""Layer 1 — Perception Module: Robust PaddleOCR engine with graceful error containment."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from app.modules.perception.normalization import normalize_plate_text

logger = logging.getLogger("trace.perception.ocr")

_OCR_INSTANCE: Optional[Any] = None
_OCR_LOCK = threading.Lock()
_OCR_INITIALIZED = False


def get_ocr_engine() -> Optional[Any]:
    """Thread-safe singleton getter for PaddleOCR."""
    global _OCR_INSTANCE, _OCR_INITIALIZED
    with _OCR_LOCK:
        if not _OCR_INITIALIZED:
            _OCR_INITIALIZED = True
            try:
                from paddleocr import PaddleOCR
                _OCR_INSTANCE = PaddleOCR(
                    use_angle_cls=False,
                    lang="en",
                    show_log=False,
                )
                logger.info("PaddleOCR engine initialized successfully.")
            except Exception as e:
                logger.warning(f"PaddleOCR failed to initialize: {e}")
                _OCR_INSTANCE = None
        return _OCR_INSTANCE


def read_plate_image(
    image_input: Union[str, Path, np.ndarray],
    min_confidence: float = 0.20,
) -> List[Dict[str, Any]]:
    """Run PaddleOCR on an image path or numpy crop.
    
    Returns a list of dicts:
    [
        {
            "raw_text": str,
            "normalized_text": str,
            "confidence": float,
            "bbox": list, # [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        }
    ]
    
    In case of no text or any exception, returns [] without raising.
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
            results = ocr.ocr(img_path, cls=False)
        elif isinstance(image_input, np.ndarray):
            if image_input.size == 0 or image_input.shape[0] < 5 or image_input.shape[1] < 5:
                return []
            results = ocr.ocr(image_input, cls=False)
        else:
            return []

        if not results or not results[0]:
            return []

        parsed: List[Dict[str, Any]] = []
        for line in results[0]:
            if not line or len(line) < 2:
                continue
            box, (text, score) = line
            conf = float(score) if score is not None else 0.0
            if conf < min_confidence:
                continue

            raw_text = str(text).strip()
            norm_text = normalize_plate_text(raw_text)
            if not norm_text:
                continue

            parsed.append({
                "raw_text": raw_text,
                "normalized_text": norm_text,
                "confidence": round(conf, 4),
                "bbox": box,
            })

        return parsed

    except Exception as e:
        logger.warning(f"[OCR WARNING] PaddleOCR inference error: {e}")
        return []

