"""Vehicle Appearance / Re-ID Feature Extractor."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
import torch
import torchvision.models as models

from app.config import settings
from app.modules.appearance.preprocessing import (
    create_transform,
    preprocess_crop,
    score_crop_quality,
    validate_crop,
    validate_crop_detailed,
)

logger = logging.getLogger("trace.appearance.extractor")

_EXTRACTOR_INSTANCE: Optional[AppearanceExtractor] = None


class AppearanceExtractor:
    """Singleton vehicle Re-ID appearance feature extractor.

    Supports:
    - resnet34_veri776: Dedicated vehicle Re-ID model trained on VeRi-776 (512-D, high separation).
    - mobilenet_v3_small: Lightweight generic baseline (1024-D, ultra-fast CPU inference).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.model_name = (model_name or settings.APPEARANCE_MODEL_NAME).lower().strip()
        self.model_path = model_path or settings.APPEARANCE_MODEL_PATH
        self.min_crop_size = settings.APPEARANCE_MIN_CROP_SIZE

        # Device selection
        req_device = (device or settings.APPEARANCE_DEVICE).lower().strip()
        if req_device == "cuda" and torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif req_device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device("cpu")

        logger.info(f"Initializing AppearanceExtractor: model={self.model_name}, device={self.device}")

        # Model resolution and loading
        self.model, self.embedding_dim, self.input_size = self._load_model()
        self.model.to(self.device)
        self.model.eval()

        self.transform = create_transform(self.input_size)
        logger.info(f"AppearanceExtractor initialized successfully (dim={self.embedding_dim}, size={self.input_size})")

    def _resolve_model_path(self, rel_or_abs_path: str) -> Optional[Path]:
        """Resolve model weight path relative to backend root or repository root."""
        p = Path(rel_or_abs_path)
        if p.is_absolute() and p.exists():
            return p

        # Search candidates
        backend_dir = Path(__file__).resolve().parents[3]  # .../backend
        repo_dir = backend_dir.parent                      # .../TRACE

        candidates = [
            backend_dir / rel_or_abs_path,
            repo_dir / rel_or_abs_path,
            backend_dir / "models" / p.name,
            repo_dir / "models" / p.name,
            p,
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _load_model(self) -> Tuple[torch.nn.Module, int, Tuple[int, int]]:
        """Load the specified model backbone and weights."""
        if self.model_name == "resnet34_veri776":
            resolved = self._resolve_model_path(self.model_path)
            if not resolved or not resolved.exists():
                logger.warning(
                    f"ResNet34 VeRi-776 weights not found at {self.model_path}. "
                    f"Falling back to MobileNetV3-Small."
                )
                return self._load_mobilenet()

            model = models.resnet34(weights=None)
            model.fc = torch.nn.Identity()

            ckpt = torch.load(resolved, map_location="cpu")
            sd = ckpt["state_dict"] if isinstance(ckpt, dict) and "state_dict" in ckpt else ckpt
            model.load_state_dict(sd, strict=False)
            return model, 512, (256, 256)

        elif self.model_name == "mobilenet_v3_small":
            return self._load_mobilenet()

        else:
            logger.warning(f"Unknown appearance model {self.model_name}, defaulting to mobilenet_v3_small")
            return self._load_mobilenet()

    def _load_mobilenet(self) -> Tuple[torch.nn.Module, int, Tuple[int, int]]:
        """Load torchvision MobileNetV3-Small as baseline feature extractor."""
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        model = models.mobilenet_v3_small(weights=weights)
        model.classifier[3] = torch.nn.Identity()
        return model, 1024, (224, 224)

    def extract_with_reason(
        self,
        crop: Optional[Union[np.ndarray, Image.Image]],
        min_size: Optional[int] = None,
    ) -> Tuple[Optional[List[float]], Optional[str]]:
        """Extract a single L2-normalized Re-ID embedding vector with diagnostic reason.

        Returns:
            (embedding_vector, None) on success.
            (None, failure_reason) on validation/inference failure.
        """
        ms = min_size if min_size is not None else self.min_crop_size
        valid_bgr, reason = validate_crop_detailed(crop, min_size=ms)
        if valid_bgr is None:
            return None, reason

        try:
            tensor = preprocess_crop(valid_bgr, self.transform).to(self.device)
            with torch.no_grad():
                feat = self.model(tensor).squeeze(0).cpu().numpy().flatten().astype(np.float32)

            if len(feat) != self.embedding_dim:
                return None, f"dimension_mismatch_{len(feat)}_expected_{self.embedding_dim}"

            if not np.isfinite(feat).all():
                return None, "non_finite_output"

            norm = float(np.linalg.norm(feat))
            if norm <= 1e-7 or not np.isfinite(norm):
                return None, "zero_norm_vector"

            normalized = feat / (norm + 1e-12)
            final_norm = float(np.linalg.norm(normalized))
            if abs(final_norm - 1.0) > 1e-2:
                return None, "norm_validation_failed"

            return [round(float(v), 6) for v in normalized], None
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return None, "inference_error"

    def extract(self, crop: Optional[np.ndarray]) -> Optional[List[float]]:
        """Extract a single L2-normalized Re-ID embedding vector from a vehicle crop."""
        emb, _ = self.extract_with_reason(crop)
        return emb

    def extract_track_embedding(
        self,
        crops: Sequence[Optional[np.ndarray]],
        max_samples: Optional[int] = None,
    ) -> Optional[List[float]]:
        """Aggregate embeddings across vehicle frames into a single track-level representation.

        Strategy:
        1. Validate crops and calculate quality score for each frame.
        2. Select the top-quality crops across the track.
        3. Extract individual L2-normalized embeddings.
        4. Mean-pool the embeddings.
        5. L2-renormalize the resulting track vector.
        """
        if not crops:
            return None

        k = max_samples or settings.APPEARANCE_MAX_TRACK_SAMPLES
        valid_crops = [c for c in crops if validate_crop(c, min_size=self.min_crop_size) is not None]

        if not valid_crops:
            return None

        # Sort crops by quality score descending
        from app.modules.appearance.preprocessing import score_crop_quality
        scored = sorted(valid_crops, key=lambda c: score_crop_quality(c), reverse=True)
        top_crops = scored[:k]

        embs: List[np.ndarray] = []
        for c in top_crops:
            vec, _ = self.extract_with_reason(c)
            if vec is not None:
                embs.append(np.asarray(vec, dtype=np.float32))

        if not embs:
            return None

        mean_vec = np.mean(embs, axis=0)
        norm = float(np.linalg.norm(mean_vec))
        if norm <= 1e-7 or not np.isfinite(norm):
            return None

        final_vec = mean_vec / (norm + 1e-12)
        return [round(float(v), 6) for v in final_vec]


def extract_vehicle_embedding(
    crop: Optional[Union[np.ndarray, Image.Image]],
    min_size: Optional[int] = None,
) -> Tuple[Optional[List[float]], Optional[str]]:
    """Convenience top-level function to extract an embedding from a vehicle crop."""
    extractor = get_appearance_extractor()
    return extractor.extract_with_reason(crop, min_size=min_size)


def get_appearance_extractor(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
) -> AppearanceExtractor:
    """Get or create the global singleton AppearanceExtractor instance."""
    global _EXTRACTOR_INSTANCE
    if _EXTRACTOR_INSTANCE is None:
        _EXTRACTOR_INSTANCE = AppearanceExtractor(model_name=model_name, device=device)
    return _EXTRACTOR_INSTANCE
