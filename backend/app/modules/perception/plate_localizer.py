"""Layer 1 — Perception Module: License plate localization, crop extraction, and preprocessing."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger("trace.perception.plate_localizer")


def load_pascal_voc_annotation(xml_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Parse Pascal VOC XML annotation file for ground-truth plate text and bounding box."""
    xml_p = Path(xml_path)
    if not xml_p.exists():
        return None

    try:
        tree = ET.parse(xml_p)
        root = tree.getroot()
        filename = root.find("filename").text if root.find("filename") is not None else xml_p.stem + ".jpg"
        
        obj = root.find("object")
        if obj is None:
            return None

        name_elem = obj.find("name")
        gt_plate = name_elem.text.strip() if name_elem is not None and name_elem.text else ""

        bndbox = obj.find("bndbox")
        if bndbox is not None:
            xmin = int(float(bndbox.find("xmin").text))
            ymin = int(float(bndbox.find("ymin").text))
            xmax = int(float(bndbox.find("xmax").text))
            ymax = int(float(bndbox.find("ymax").text))
            bbox = [xmin, ymin, xmax, ymax]
        else:
            bbox = []

        return {
            "filename": filename,
            "ground_truth_plate": gt_plate,
            "bbox": bbox,
        }
    except Exception as e:
        logger.warning(f"Error parsing annotation {xml_path}: {e}")
        return None


def locate_plate_candidate(image: np.ndarray) -> Optional[List[int]]:
    """Detect candidate license plate bounding box using contrast, morphology, and contour filtering."""
    if image is None or image.size == 0 or image.shape[0] < 20 or image.shape[1] < 20:
        return None
    try:
        h, w = image.shape[:2]
        # Bumper search band: 25% to 85% of vehicle height
        search_y1 = int(h * 0.25)
        search_y2 = int(h * 0.85)
        roi = image[search_y1:search_y2, :]
        rh, rw = roi.shape[:2]
        if rh < 10 or rw < 20:
            return None

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, rect_kernel)
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kernel)
        contrast = cv2.add(gray, tophat)
        contrast = cv2.subtract(contrast, blackhat)

        grad_x = cv2.Sobel(contrast, cv2.CV_32F, 1, 0, ksize=3)
        grad_x = cv2.convertScaleAbs(grad_x)
        grad_x = cv2.GaussianBlur(grad_x, (5, 5), 0)

        _, thresh = cv2.threshold(grad_x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, close_kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            aspect = float(cw) / max(1, ch)
            area = cw * ch
            cx = x + cw / 2.0
            # Horizontal center should be within 20% to 80% of vehicle width
            # Candidate plate width must be at least 25% of vehicle width to filter out small emblems
            if 1.8 <= aspect <= 6.5 and cw >= int(rw * 0.25) and cw <= int(rw * 0.85) and ch >= 12:
                if 0.20 * rw <= cx <= 0.80 * rw:
                    patch = gray[y:y + ch, x:x + cw]
                    center_dist = abs(cx - rw / 2.0) / (rw / 2.0)
                    score = (float(np.std(patch)) * area) / (1.0 + 0.5 * center_dist)
                    candidates.append((score, [x, search_y1 + y, x + cw, search_y1 + y + ch]))

        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]
        return None
    except Exception:
        return None


def extract_plate_crop(
    image: np.ndarray,
    bbox: Optional[List[int]] = None,
    scale_factor: float = 2.5,
) -> np.ndarray:
    """Crop license plate region from vehicle image and enhance resolution for OCR.
    
    If bbox is provided ([xmin, ymin, xmax, ymax]), crops that specific rectangle with context padding.
    If bbox is None, uses contrast/morphological plate candidate localization, falling back to a safe bumper ROI.
    """
    if image is None or image.size == 0:
        return np.empty((0, 0, 3), dtype=np.uint8)

    h, w = image.shape[:2]

    if bbox and len(bbox) == 4:
        x1, y1, x2, y2 = bbox
        pad_x = max(2, int((x2 - x1) * 0.08))
        pad_y = max(2, int((y2 - y1) * 0.12))
        
        crop_x1 = max(0, x1 - pad_x)
        crop_y1 = max(0, y1 - pad_y)
        crop_x2 = min(w, x2 + pad_x)
        crop_y2 = min(h, y2 + pad_y)
        crop = image[crop_y1:crop_y2, crop_x1:crop_x2]
    else:
        candidate_box = locate_plate_candidate(image)
        if candidate_box and len(candidate_box) == 4:
            x1, y1, x2, y2 = candidate_box
            pad_x = max(4, int((x2 - x1) * 0.10))
            pad_y = max(4, int((y2 - y1) * 0.20))
            crop_x1 = max(0, x1 - pad_x)
            crop_y1 = max(0, y1 - pad_y)
            crop_x2 = min(w, x2 + pad_x)
            crop_y2 = min(h, y2 + pad_y)
            crop = image[crop_y1:crop_y2, crop_x1:crop_x2]
        else:
            # Safe bumper crop: 45% to 90% height, 12% to 88% width
            crop_y1 = int(h * 0.45)
            crop_y2 = int(h * 0.90)
            crop_x1 = int(w * 0.12)
            crop_x2 = int(w * 0.88)
            crop = image[crop_y1:crop_y2, crop_x1:crop_x2]

    if crop.size == 0 or crop.shape[0] < 4 or crop.shape[1] < 4:
        crop = image

    # Upscale crop with bicubic interpolation for clean OCR edge detection
    target_w = max(180, int(crop.shape[1] * scale_factor))
    target_h = max(60, int(crop.shape[0] * scale_factor))
    
    resized = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
    return resized

