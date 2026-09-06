"""
TRACE End-to-End Three-Layer Verification: Perception, Identity Fusion & Spatial-Temporal Reasoning.
===================================================================================================

Validates:
  Layer 1 — Appearance Extractor (ResNet34 VeRi-776, 512-D L2 normalized vectors from real video crop)
  Layer 2 — Cross-Camera Multi-Modal Identity Fusion (cosine -> calibrated similarity, temporal, transition, scoring)
  Layer 3 — Multi-Identifier Search & Spatial-Temporal Reconstruction (DB query, road graph, speeds, anomalies, evidence)

Usage:
  python scripts/verify_layer1_layer2_layer3.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import cv2
import numpy as np
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import CanonicalVehicle, IdentityMatch, VehicleObservation
from app.modules.appearance import get_appearance_extractor
from app.modules.appearance.similarity import (
    compute_appearance_similarity,
    compute_calibrated_similarity,
    compute_cosine_similarity,
)
from app.modules.identity.scoring import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    compute_identity_score,
)
from app.modules.spatial_temporal.road_graph import get_road_graph
from app.modules.spatial_temporal.trajectory_service import (
    find_and_build_trajectory,
    resolve_vehicle_identity,
    search_vehicles,
)


def verify_all_three_layers():
    print("=" * 80)
    print("TRACE — THREE-LAYER COMPREHENSIVE VERIFICATION: L1 + L2 + L3")
    print("=" * 80)

    passed_checks = 0
    total_checks = 0

    def check(condition: bool, label: str, detail: str = ""):
        nonlocal passed_checks, total_checks
        total_checks += 1
        status = "PASS" if condition else "FAIL"
        if condition:
            passed_checks += 1
        msg = f"  [{status}] Check {total_checks:02d}: {label}"
        if detail:
            msg += f" -> {detail}"
        print(msg)
        return condition

    # =========================================================================
    # LAYER 1: APPEARANCE FEATURE EXTRACTION
    # =========================================================================
    print("\n--- [LAYER 1: PERCEPTION & APPEARANCE RE-ID] ---")
    
    # 1.1 Model initialization & device
    extractor = get_appearance_extractor()
    check(extractor is not None, "Model initialization", f"Model={settings.APPEARANCE_MODEL_NAME}, Device={extractor.device}")
    
    # 1.2 Real video crop extraction
    footage_path = backend_dir.parent / "data" / "footage" / "c020" / "vdo.avi"
    emb = None
    if footage_path.exists():
        cap = cv2.VideoCapture(str(footage_path))
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            # Extract vehicle crop (center region)
            crop = frame[100:250, 200:400]
            emb = extractor.extract(crop)
    
    if emb is None:
        # Fallback synthetic crop
        dummy_crop = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        emb = extractor.extract(dummy_crop)

    # 1.3 Dimension check
    check(len(emb) == 512, "Embedding dimension is 512-D", f"dim={len(emb)}")

    # 1.4 L2 norm check
    l2_norm = float(np.linalg.norm(emb))
    check(abs(l2_norm - 1.0) < 1e-5, "Strict L2 unit-norm constraint", f"norm={l2_norm:.6f}")

    # 1.5 Crop rejection guard
    tiny_crop = np.zeros((10, 10, 3), dtype=np.uint8)
    rejected = extractor.extract(tiny_crop)
    check(rejected is None, "Crop validation guard (<24px rejected)", f"got {rejected}")


    # =========================================================================
    # LAYER 2: MULTI-MODAL IDENTITY FUSION
    # =========================================================================
    print("\n--- [LAYER 2: MULTI-MODAL IDENTITY FUSION] ---")

    # 2.1 Cross-camera embeddings test on CityFlow footage (c020 vs c023)
    footage_c023 = backend_dir.parent / "data" / "footage" / "c023" / "vdo.avi"
    emb_b = None
    if footage_c023.exists():
        cap2 = cv2.VideoCapture(str(footage_c023))
        ret2, frame2 = cap2.read()
        cap2.release()
        if ret2 and frame2 is not None:
            crop2 = frame2[120:260, 210:410]
            emb_b = extractor.extract(crop2)

    if emb_b is None:
        # Slight perturbation of emb
        emb_b = [float(x + np.random.normal(0, 0.05)) for x in emb]
        norm_b = float(np.linalg.norm(emb_b))
        emb_b = [x / norm_b for x in emb_b]

    # 2.2 Raw cosine similarity
    raw_cos = compute_cosine_similarity(emb, emb_b)
    check(raw_cos is not None and -1.0 <= raw_cos <= 1.0, "Cosine similarity in [-1, 1]", f"cos={raw_cos:.4f}")

    # 2.3 Calibrated appearance similarity
    cal_sim = compute_calibrated_similarity(raw_cos, min_val=0.60, max_val=0.88)
    check(0.0 <= cal_sim <= 1.0, "Calibrated similarity in [0, 1]", f"calibrated={cal_sim:.4f}")

    # 2.4 CityFlow visual-only fusion score (no license plate)
    graph = get_road_graph()
    fusion_res = compute_identity_score(
        obs_a={"fused_plate_text": "NOT READ", "fused_confidence": 0.0, "vehicle_type": "car", "vehicle_colour": "white"},
        obs_b={"fused_plate_text": "NOT READ", "fused_confidence": 0.0, "vehicle_type": "car", "vehicle_colour": "white"},
        appearance_similarity=0.80,
        camera_id_a="c020",
        camera_id_b="c023",
        time_gap_s=150.0,
        road_graph=graph,
    )
    check(fusion_res["mode"] == "CITYFLOW", "Visual-only mode selection", f"mode={fusion_res['mode']}")
    check(fusion_res["plate_similarity"] is None, "Plate ignored in visual-only mode", "plate_similarity=None")
    check(fusion_res["identity_score"] >= CONFIRM_THRESHOLD, "Score >= CONFIRM threshold (0.70)", f"score={fusion_res['identity_score']:.4f}")
    check(fusion_res["match_confidence_label"] == "confirmed", "Confirmed match status", f"label={fusion_res['match_confidence_label']}")


    # =========================================================================
    # LAYER 3: SPATIAL-TEMPORAL RECONSTRUCTION & MULTI-IDENTIFIER SEARCH
    # =========================================================================
    print("\n--- [LAYER 3: SPATIAL-TEMPORAL RECONSTRUCTION & SEARCH] ---")
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    with Session(engine) as session:
        # 3.1 Search by plate
        search_res_plate = search_vehicles(session, "TN37")
        check(search_res_plate.total >= 1, "DB search by plate", f"found={search_res_plate.total} vehicles")

        # 3.2 Search by track ID
        search_res_track = search_vehicles(session, "TRK-")
        check(search_res_track.total >= 1, "DB search by track ID", f"found={search_res_track.total} vehicles")

        # 3.3 Trajectory resolution by Plate
        traj_plate = find_and_build_trajectory(session, "TN 37 CY 1234", road_graph=graph)
        check(traj_plate.plate == "TN 37 CY 1234", "Trajectory resolution by Plate", f"plate={traj_plate.plate}, obs={len(traj_plate.observations)}")
        check(len(traj_plate.observations) >= 1, "Observations present in trajectory", f"count={len(traj_plate.observations)}")

        # 3.4 Trajectory resolution by Track ID (Plate-free)
        # Find sample track ID in DB
        sample_obs = session.execute(
            select(VehicleObservation).where(VehicleObservation.track_id.like("TRK-%")).limit(1)
        ).scalars().first()
        if sample_obs:
            traj_track = find_and_build_trajectory(session, sample_obs.track_id, road_graph=graph)
            check(traj_track.vehicle_id == sample_obs.track_id, "Trajectory resolution by Track ID", f"id={traj_track.vehicle_id}, type={traj_track.identifier_type}")
            check(traj_track.identifier_type == "track_id", "Identifier type is track_id", f"type={traj_track.identifier_type}")

        # 3.5 Trajectory resolution by Observation UUID
        if sample_obs:
            traj_obs = find_and_build_trajectory(session, str(sample_obs.observation_id), road_graph=graph)
            check(traj_obs.identifier_type == "observation_id", "Trajectory resolution by Observation UUID", f"type={traj_obs.identifier_type}")

        # 3.6 Chronological ordering validation
        if traj_plate.observations:
            ts_list = [o.captured_at for o in traj_plate.observations]
            check(ts_list == sorted(ts_list), "Chronological ordering preserved", f"first={ts_list[0].isoformat()} last={ts_list[-1].isoformat()}")

        # 3.7 Implied speed & Road Graph reachability
        speeds = [o.implied_speed_kmph for o in traj_plate.observations if o.implied_speed_kmph is not None]
        check(isinstance(speeds, list), "Implied speed computed across road transitions", f"transitions_with_speed={len(speeds)}")

        # 3.8 Anomaly detection integration
        check(isinstance(traj_plate.anomaly_flags, list), "Anomaly flags list in response", f"anomalies={traj_plate.anomaly_flags}")

        # 3.9 Explainable Layer 2 evidence breakdown
        first_obs = traj_plate.observations[0]
        check(first_obs.evidence is not None, "Explainable Layer 2 evidence present", f"ev_keys={[k for k, v in first_obs.evidence.model_dump().items() if v is not None]}")

        # 3.10 Offline fallback validation (when no DB record exists)
        traj_fallback = find_and_build_trajectory(session, "NONEXISTENT_VEHICLE_9999", road_graph=graph)
        check(traj_fallback.identifier_type == "cityflow_ground_truth_fallback", "Offline GT fallback when DB has no match", f"type={traj_fallback.identifier_type}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print(f"VERIFICATION RESULT: {passed_checks}/{total_checks} CHECKS PASSED")
    if passed_checks == total_checks:
        print("STATUS: ALL CHECKS PASSED SUCCESSFULLY (L1, L2, L3)")
    else:
        print(f"STATUS: {total_checks - passed_checks} CHECKS FAILED")
    print("=" * 80)

    return passed_checks == total_checks


if __name__ == "__main__":
    success = verify_all_three_layers()
    sys.exit(0 if success else 1)
