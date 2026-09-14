"""Vehicle Crop Preprocessing and Validation for Re-ID Feature Extraction."""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image

logger = logging.getLogger("trace.appearance.preprocessing")

# Standard ImageNet normalization constants
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def validate_crop_detailed(
    crop: Optional[Union[np.ndarray, Image.Image]],
    min_size: int = 24,
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Validate vehicle crop and return (valid_bgr, failure_reason).
    
    Supports BGR, RGB (PIL), Grayscale, and BGRA conversions.
    """
    if crop is None:
        return None, "missing_crop"

    if isinstance(crop, Image.Image):
        try:
            arr = np.array(crop)
            if len(arr.shape) == 2:
                crop = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            elif arr.shape[2] == 4:
                crop = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            else:
                crop = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.debug(f"Failed to convert PIL crop to numpy BGR: {e}")
            return None, "invalid_image_format"

    if not isinstance(crop, np.ndarray):
        return None, "invalid_data_type"

    if crop.size == 0:
        return None, "empty_crop"

    # Convert 2D grayscale to 3-channel BGR
    if len(crop.shape) == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    elif len(crop.shape) == 3 and crop.shape[2] == 1:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    elif len(crop.shape) == 3 and crop.shape[2] == 4:
        # Convert BGRA to BGR
        crop = cv2.cvtColor(crop, cv2.COLOR_BGRA2BGR)
    elif len(crop.shape) != 3 or crop.shape[2] != 3:
        return None, "invalid_channels"

    h, w = crop.shape[:2]
    if h < min_size or w < min_size:
        return None, "crop_too_small"

    if not np.isfinite(crop).all():
        return None, "non_finite_values"

    return crop, None


def validate_crop(
    crop: Optional[Union[np.ndarray, Image.Image]],
    min_size: int = 24,
) -> Optional[np.ndarray]:
    """Validate that an input vehicle crop is non-empty, non-corrupt, and sufficiently large.

    Args:
        crop: Numpy BGR array or PIL Image.
        min_size: Minimum width and height in pixels.

    Returns:
        Valid BGR numpy array, or None if crop fails validation.
    """
    valid_bgr, _ = validate_crop_detailed(crop, min_size=min_size)
    return valid_bgr


def score_crop_quality(
    crop: Optional[np.ndarray],
    bbox: Optional[Sequence[float]] = None,
    frame_shape: Optional[Tuple[int, int]] = None,
    conf: float = 1.0,
) -> float:
    """Calculate quality score in [0.0, 1.0] for a vehicle crop.
    
    Factors:
    - Bounding-box area (larger resolution = more discriminative details)
    - Sharpness (variance of Laplacian, penalizes motion blur/defocus)
    - Boundary clearance (penalizes vehicle being clipped at camera frame edge)
    - Detection confidence
    """
    valid = validate_crop(crop, min_size=16)
    if valid is None:
        return 0.0

    h, w = valid.shape[:2]
    
    # 1. Area score: saturates at 200x200 (40,000 px)
    area = float(h * w)
    area_score = min(1.0, area / 40000.0)

    # 2. Sharpness score: normalized Laplacian variance
    try:
        gray = cv2.cvtColor(valid, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # lap_var typical range: 10 (blurry) to 300+ (sharp)
        sharp_score = min(1.0, lap_var / 250.0)
    except Exception:
        sharp_score = 0.5

    # 3. Boundary clearance: penalize crops clipped by frame edge
    boundary_score = 1.0
    if bbox is not None and frame_shape is not None:
        x1, y1, x2, y2 = bbox[:4]
        fh, fw = frame_shape[:2]
        margin = 3.0
        if x1 <= margin or y1 <= margin or x2 >= (fw - margin) or y2 >= (fh - margin):
            boundary_score = 0.5  # clipped at frame boundary

    # 4. Confidence
    c_score = max(0.0, min(1.0, float(conf)))

    # Weighted composite quality
    composite = (0.35 * area_score) + (0.35 * sharp_score) + (0.15 * boundary_score) + (0.15 * c_score)
    return round(float(composite), 4)


def create_transform(target_size: Tuple[int, int] = (256, 256)) -> T.Compose:
    """Create torchvision transform pipeline for vehicle Re-ID inference."""
    return T.Compose([
        T.Resize(target_size),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def preprocess_crop(
    crop: np.ndarray,
    transform: T.Compose,
) -> torch.Tensor:
    """Convert validated BGR vehicle crop to model input tensor (1, 3, H, W)."""
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    tensor = transform(pil_img)
    return tensor.unsqueeze(0)
