"""Layer 1 — Perception Module: Robust PaddleOCR engine with graceful error containment."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from app.modules.perception.normalization import normalize_plate_text

logger = logging.getLogger("trace.perception.ocr")

_OCR_INSTANCE: Optional[Any] = None
_OCR_LOCK = threading.Lock()
_OCR_CALL_LOCK = threading.Lock()
_OCR_INITIALIZED = False


def get_ocr_engine() -> Optional[Any]:
    """Thread-safe singleton getter for PaddleOCR."""
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

                import paddleocr.paddleocr
                # Look for local workspace models first to support sandboxed execution
                local_paddle_dirs = [
                    Path(__file__).resolve().parents[3] / "models" / ".paddleocr",
                    Path.cwd() / "backend" / "models" / ".paddleocr",
                    Path.cwd() / "models" / ".paddleocr",
                ]
                for lp in local_paddle_dirs:
                    if lp.exists() and (lp / "whl").exists():
                        paddleocr.paddleocr.BASE_DIR = str(lp).replace("\\", "/") + "/"
                        break

                from paddleocr import PaddleOCR
                use_gpu = False
                try:
                    import paddle
                    if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
                        use_gpu = True
                except Exception:
                    use_gpu = False

                _OCR_INSTANCE = PaddleOCR(
                    use_angle_cls=False,
                    lang="en",
                    enable_mkldnn=False,
                    use_gpu=use_gpu,
                    cpu_threads=2,
                    show_log=False,
                )
                logger.info(f"PaddleOCR engine initialized successfully (gpu={use_gpu}).")
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
        with _OCR_CALL_LOCK:
            if isinstance(image_input, (str, Path)):
                img_path = str(image_input)
                if not Path(img_path).exists():
                    logger.warning(f"[OCR WARNING] Image file not found: {img_path}")
                    return []
                results = ocr.ocr(img_path, cls=False)
            elif isinstance(image_input, np.ndarray):
                if image_input.size == 0 or image_input.shape[0] < 8 or image_input.shape[1] < 8:
                    return []
                
                # Ensure standard 3-channel BGR uint8 image
                inp = image_input
                if inp.ndim == 2:
                    inp = cv2.cvtColor(inp, cv2.COLOR_GRAY2BGR)
                elif inp.ndim == 3 and inp.shape[2] == 1:
                    inp = cv2.cvtColor(inp, cv2.COLOR_GRAY2BGR)
                elif inp.ndim == 3 and inp.shape[2] == 4:
                    inp = cv2.cvtColor(inp, cv2.COLOR_BGRA2BGR)
                elif inp.ndim != 3 or inp.shape[2] != 3:
                    return []

                inp = np.ascontiguousarray(inp, dtype=np.uint8)
                results = ocr.ocr(inp, cls=False)
            else:
                return []

        if not results or not results[0]:
            return []

        parsed: List[Dict[str, Any]] = []
        raw_lines = results[0] if (results and len(results) > 0 and results[0] is not None) else []
        for line in raw_lines:
            if line is None:
                continue
            try:
                # Handle varying tuple / list / ndarray formats from PaddleOCR
                if isinstance(line, (list, tuple)):
                    if len(line) < 2:
                        continue
                    box = line[0]
                    text_data = line[1]
                elif isinstance(line, np.ndarray):
                    if line.shape[0] < 2:
                        continue
                    box = line[0]
                    text_data = line[1]
                else:
                    continue

                if isinstance(text_data, (tuple, list)):
                    if len(text_data) >= 2:
                        text, score = text_data[0], text_data[1]
                    elif len(text_data) == 1:
                        text, score = text_data[0], 0.5
                    else:
                        continue
                elif isinstance(text_data, np.ndarray):
                    if text_data.size >= 2:
                        text, score = text_data.flat[0], text_data.flat[1]
                    elif text_data.size == 1:
                        text, score = text_data.flat[0], 0.5
                    else:
                        continue
                elif isinstance(text_data, str):
                    text, score = text_data, 0.5
                else:
                    continue

                conf = float(score) if score is not None else 0.0
                if conf < min_confidence:
                    continue

                raw_text = str(text).strip()
                norm_text = normalize_plate_text(raw_text)
                if not norm_text:
                    continue

                bbox_list = box.tolist() if hasattr(box, "tolist") else box

                parsed.append({
                    "raw_text": raw_text,
                    "normalized_text": norm_text,
                    "confidence": round(conf, 4),
                    "bbox": bbox_list,
                })
            except Exception:
                continue

        return parsed

    except Exception as e:
        logger.debug(f"[OCR] PaddleOCR inference error on crop: {e}")
        return []

