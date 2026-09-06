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
    if crop is None:
        return None

    if isinstance(crop, Image.Image):
        try:
            crop = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.debug(f"Failed to convert PIL crop to numpy BGR: {e}")
            return None

    if not isinstance(crop, np.ndarray):
        return None

    if crop.size == 0 or len(crop.shape) != 3 or crop.shape[2] != 3:
        return None

    h, w = crop.shape[:2]
    if h < min_size or w < min_size:
        return None

    if not np.isfinite(crop).all():
        return None

    return crop


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
