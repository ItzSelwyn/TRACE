"""End-to-End CityFlowV2 Vehicle Re-ID and Multi-Modal Identity Fusion Validation.

Uses REAL video frames from CityFlowV2 (c020/vdo.avi and c023/vdo.avi).
Ground-truth annotations are used SOLELY as evaluation labels to extract crops.
The identity algorithm operates completely without ground-truth labels and with plate=None.
"""

import json
from datetime import datetime, timezone
import cv2
import numpy as np
import pytest

from app.modules.appearance import (
    get_appearance_extractor,
    compute_appearance_similarity,
    compute_cosine_similarity,
)
from app.modules.identity.scoring import (
    CONFIRM_THRESHOLD,
    CANDIDATE_THRESHOLD,
    compute_identity_score,
)


def _load_vehicle_records(vehicle_id, camera_id):
    """Helper to load ground-truth evaluation bounding boxes for a vehicle."""
    records = []
    with open("D:/coding/TRACE/data/ground_truth/cityflow_train_gt.jsonl", "r") as f:
        for line in f:
            d = json.loads(line)
            if d["vehicle_id"] == vehicle_id and d["camera_id"] == camera_id:
                records.append(d)
    return records


def _extract_crops_from_video(video_path, records, num_samples=5):
    """Extract real vehicle bounding box crops from actual video frames."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    step = max(1, len(records) // num_samples)
    samples = records[::step][:num_samples]
    crops = []
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    for s in samples:
        frame_idx = s["frame_id"]
        bbox = s["bbox"]
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx - 1)
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        x, y, w, h = int(bbox["x"]), int(bbox["y"]), int(bbox["width"]), int(bbox["height"])
        crop = frame[max(0, y):min(H, y + h), max(0, x):min(W, x + w)]
        if crop.size > 0 and crop.shape[0] >= 24 and crop.shape[1] >= 24:
            crops.append(crop)

    cap.release()
    return crops


def test_cityflow_cross_camera_positive_pair_confirmed():
    """Evaluate same vehicle (Vehicle 260) across c020 and c023 with plate=None.

    Must achieve CONFIRMED status via genuine visual appearance + temporal + camera transition.
    """
    recs_c020 = _load_vehicle_records(260, "c020")
    recs_c023 = _load_vehicle_records(260, "c023")
    assert len(recs_c020) > 0 and len(recs_c023) > 0, "Evaluation data missing"

    crops_c020 = _extract_crops_from_video("D:/coding/TRACE/data/footage/c020/vdo.avi", recs_c020)
    crops_c023 = _extract_crops_from_video("D:/coding/TRACE/data/footage/c023/vdo.avi", recs_c023)
    assert len(crops_c020) > 0 and len(crops_c023) > 0, "Could not extract video crops"

    extractor = get_appearance_extractor()
    emb_c020 = extractor.extract_track_embedding(crops_c020)
    emb_c023 = extractor.extract_track_embedding(crops_c023)

    assert emb_c020 is not None and emb_c023 is not None
    assert len(emb_c020) == extractor.embedding_dim
    assert len(emb_c023) == extractor.embedding_dim

    raw_cosine = compute_cosine_similarity(emb_c020, emb_c023)
    app_sim = compute_appearance_similarity(emb_c020, emb_c023)

    assert raw_cosine is not None
    assert app_sim is not None
    assert app_sim > 0.0, f"Expected positive appearance similarity, got {app_sim}"

    # Feed into Layer 2 multi-modal identity scorer (plate=None)
    obs_a = {
        "fused_plate_text": None,  # Plate unavailable (CityFlowV2)
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "captured_at": "2024-01-01T10:00:00Z",
        "camera_id": "c020",
    }
    obs_b = {
        "fused_plate_text": None,  # Plate unavailable (CityFlowV2)
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "captured_at": "2024-01-01T10:05:00Z",
        "camera_id": "c023",
    }

    result = compute_identity_score(
        obs_a, obs_b,
        appearance_similarity=app_sim,
        camera_id_a="c020",
        camera_id_b="c023",
        time_gap_s=300.0,
    )

    assert result["mode"] == "CITYFLOW"
    assert result["plate_similarity"] is None
    assert result["appearance_similarity"] == app_sim
    assert result["temporal_score"] == 1.0
    assert result["camera_transition_score"] == 1.0
    assert result["status"] == "CONFIRMED", (
        f"Cross-camera vehicle 260 expected CONFIRMED, got {result['status']} (score={result['identity_score']:.4f})"
    )
    assert result["identity_score"] >= CONFIRM_THRESHOLD


def test_cityflow_cross_camera_negative_pair_distinguished():
    """Evaluate different vehicles (Vehicle 260 in c020 vs Vehicle 265 in c023).

    Must produce lower appearance similarity than same vehicle.
    """
    recs_260_c020 = _load_vehicle_records(260, "c020")
    recs_260_c023 = _load_vehicle_records(260, "c023")
    recs_265_c023 = _load_vehicle_records(265, "c023")

    crops_260_c020 = _extract_crops_from_video("D:/coding/TRACE/data/footage/c020/vdo.avi", recs_260_c020)
    crops_260_c023 = _extract_crops_from_video("D:/coding/TRACE/data/footage/c023/vdo.avi", recs_260_c023)
    crops_265_c023 = _extract_crops_from_video("D:/coding/TRACE/data/footage/c023/vdo.avi", recs_265_c023)

    extractor = get_appearance_extractor()
    emb_260_c020 = extractor.extract_track_embedding(crops_260_c020)
    emb_260_c023 = extractor.extract_track_embedding(crops_260_c023)
    emb_265_c023 = extractor.extract_track_embedding(crops_265_c023)

    cos_pos = compute_cosine_similarity(emb_260_c020, emb_260_c023)
    cos_neg = compute_cosine_similarity(emb_260_c020, emb_265_c023)

    assert cos_pos is not None and cos_neg is not None
    assert cos_pos > cos_neg, f"Positive cosine ({cos_pos}) must be higher than negative cosine ({cos_neg})"
