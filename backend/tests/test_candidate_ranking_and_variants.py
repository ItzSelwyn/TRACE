"""Unit tests for plate candidate ranking and preprocessing variants."""

import numpy as np
import pytest

from app.modules.perception.candidate_ranking import (
    boundary_clipping_penalty,
    brightness_contrast_score,
    dimension_score,
    laplacian_sharpness,
    motion_blur_score,
    score_candidate_frame,
)
from app.modules.perception.preprocessing_variants import (
    generate_preprocessing_variants,
    perspective_deskew,
)


def test_laplacian_sharpness_differentiates_blur():
    sharp_img = np.zeros((60, 180, 3), dtype=np.uint8)
    # Add strong high-frequency checkerboard / text pattern
    sharp_img[::4, ::4] = 255
    sharp_img[1::4, 1::4] = 128

    blurry_img = np.ones((60, 180, 3), dtype=np.uint8) * 128

    score_sharp = laplacian_sharpness(sharp_img)
    score_blurry = laplacian_sharpness(blurry_img)

    assert score_sharp > score_blurry
    assert score_blurry < 5.0
    assert score_sharp > 50.0


def test_motion_blur_score():
    img = np.ones((60, 180, 3), dtype=np.uint8) * 100
    # Add horizontal streaks (motion blur)
    img[10:50, :] = 200

    score = motion_blur_score(img)
    assert 0.0 <= score <= 1.0


def test_dimension_score():
    # Ideal aspect ratio (3.5) and good size
    good_crop = np.zeros((40, 140, 3), dtype=np.uint8)
    good_score = dimension_score(good_crop)

    # Tiny crop
    bad_crop = np.zeros((8, 20, 3), dtype=np.uint8)
    bad_score = dimension_score(bad_crop)

    assert good_score > bad_score
    assert good_score >= 0.70


def test_boundary_clipping_penalty():
    frame_shape = (360, 640, 3)

    # Safe box in middle of frame
    safe_box = [100, 100, 200, 150]
    pen_safe = boundary_clipping_penalty(safe_box, frame_shape)
    assert pen_safe == 1.0

    # Box clipped at frame top-left edge
    clipped_box = [1, 2, 100, 50]
    pen_clipped = boundary_clipping_penalty(clipped_box, frame_shape)
    assert pen_clipped < 1.0


def test_composite_candidate_ranking():
    crop = np.zeros((40, 150, 3), dtype=np.uint8)
    crop[::4, ::4] = 255

    res = score_candidate_frame(
        crop=crop,
        bbox=[50, 50, 200, 90],
        frame_shape=(360, 640, 3),
        det_conf=0.90,
    )
    assert "composite_score" in res
    assert 0.0 <= res["composite_score"] <= 1.0
    assert "is_promising" in res


def test_generate_preprocessing_variants():
    crop = np.zeros((30, 120, 3), dtype=np.uint8)
    crop[5:25, 10:110] = 180

    variants = generate_preprocessing_variants(crop)
    var_names = [v[0] for v in variants]

    assert "ORIGINAL" in var_names
    assert "UPSCALE_2X" in var_names
    assert "GRAYSCALE" in var_names
    assert "CLAHE" in var_names
    assert "DENOISED_SHARPEN" in var_names

    for name, img in variants:
        assert img is not None
        assert img.size > 0
        assert img.shape[0] >= 30
        assert img.shape[1] >= 100
