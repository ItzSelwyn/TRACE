"""Vehicle Appearance / Re-ID Feature Extraction Package."""

from app.modules.appearance.extractor import (
    AppearanceExtractor,
    get_appearance_extractor,
)
from app.modules.appearance.preprocessing import (
    validate_crop,
    preprocess_crop,
)
from app.modules.appearance.similarity import (
    compute_appearance_similarity,
    compute_calibrated_similarity,
    compute_cosine_similarity,
)


def extract_vehicle_embedding(crop):
    """Convenience helper to extract embedding from a single vehicle crop."""
    return get_appearance_extractor().extract(crop)


__all__ = [
    "AppearanceExtractor",
    "get_appearance_extractor",
    "extract_vehicle_embedding",
    "compute_appearance_similarity",
    "compute_calibrated_similarity",
    "compute_cosine_similarity",
    "validate_crop",
    "preprocess_crop",
]
