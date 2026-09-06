"""Unit and integration tests for Layer 1 Perception pipeline components."""

import numpy as np
import pytest

from app.modules.perception.normalization import compute_character_accuracy, normalize_plate_text
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.plate_localizer import extract_plate_crop
from app.modules.perception.temporal_fusion import TemporalOCRFusion


def test_normalization_indian_plates():
    assert normalize_plate_text("TN 37 CY 1234") == "TN37CY1234"
    assert normalize_plate_text("tn-09-ab-4567") == "TN09AB4567"
    assert normalize_plate_text("TN.63.BV.7954") == "TN63BV7954"
    assert normalize_plate_text("  KA 01  MH  9999  ") == "KA01MH9999"
    assert normalize_plate_text("") == ""
    assert normalize_plate_text(None) == ""


def test_character_accuracy():
    assert compute_character_accuracy("TN37CY1234", "TN37CY1234") == 1.0
    assert compute_character_accuracy("TN37CY1234", "TN37CY1235") == 0.90
    assert compute_character_accuracy("", "TN37CY1234") == 0.0


def test_extract_plate_crop_shape():
    dummy = np.zeros((200, 300, 3), dtype=np.uint8)
    crop = extract_plate_crop(dummy, bbox=[50, 60, 150, 100])
    assert crop.shape[0] > 0
    assert crop.shape[1] > 0


def test_temporal_ocr_fusion_logic():
    fusion = TemporalOCRFusion()
    
    # Track 1: Clear multi-frame agreement
    fusion.add_ocr_read(camera_id="CAM020", track_id="TRK-001", frame_id=1, raw_text="TN 37 CY 1234", confidence=0.75)
    fusion.add_ocr_read(camera_id="CAM020", track_id="TRK-001", frame_id=2, raw_text="TN37CY1234", confidence=0.88)
    fusion.add_ocr_read(camera_id="CAM020", track_id="TRK-001", frame_id=3, raw_text="TN37CY1234", confidence=0.95)

    res = fusion.fuse_track(camera_id="CAM020", track_id="TRK-001", vehicle_type="car", vehicle_colour="white")
    assert res["track_id"] == "TRK-001"
    assert res["fused_plate_text"] == "TN37CY1234"
    assert res["fused_confidence"] >= 0.95
    assert res["ocr_samples_count"] == 3


def test_normalization_noise_and_confusions():
    # Leading noise stripping before valid state code
    assert normalize_plate_text("ETN638V7954") == "TN63BV7954"
    # IND badge stripping
    assert normalize_plate_text("INDTN47T4464") == "TN47T4464"
    # RTO single-digit padding
    assert normalize_plate_text("TN 7 AP 0659") == "TN07AP0659"
    # Letter-to-digit in RTO (O/G -> 0)
    assert normalize_plate_text("TNO7BT5778") == "TN07BT5778"
    assert normalize_plate_text("TNG2AU9295") == "TN02AU9295"
    # Digit-to-letter in series (3 -> J, 8 -> B)
    assert normalize_plate_text("TN69A34455") == "TN69AJ4455"
    # State code substitution (IN -> TN)
    assert normalize_plate_text("IN69A34455") == "TN69AJ4455"


def test_detect_crop_color_palette():
    from app.modules.perception.pipeline import _detect_crop_color

    # Synthetic color swatches
    def _swatch(b, g, r):
        arr = np.zeros((80, 80, 3), dtype=np.uint8)
        arr[:, :, 0] = b
        arr[:, :, 1] = g
        arr[:, :, 2] = r
        return arr

    assert _detect_crop_color(_swatch(20, 20, 220)) == "RED"
    assert _detect_crop_color(_swatch(25, 110, 220)) == "ORANGE"
    assert _detect_crop_color(_swatch(20, 200, 220)) == "YELLOW"
    assert _detect_crop_color(_swatch(20, 180, 40)) == "GREEN"
    assert _detect_crop_color(_swatch(200, 80, 20)) == "BLUE"
    assert _detect_crop_color(_swatch(30, 30, 30)) == "BLACK"
    assert _detect_crop_color(_swatch(135, 135, 135)) == "SILVER"
    assert _detect_crop_color(_swatch(240, 240, 240)) == "WHITE"


