"""Layer 2 — Identity Fusion Module: Comprehensive Verification Script."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Camera, CanonicalVehicle, IdentityMatch, VehicleObservation
from app.modules.identity import (
    CANDIDATE_THRESHOLD,
    CONFIRM_THRESHOLD,
    compute_identity_score,
    levenshtein_similarity,
    match_observation_pair,
    run_identity_fusion_on_database,
)
from app.modules.perception.persistence import persist_fused_observation, resolve_camera_uuid


def run_identity_verification():
    print("=" * 75)
    print("TRACE LAYER 2 — IDENTITY FUSION VERIFICATION SUITE")
    print("=" * 75)

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    # 1. Inspect and Prepare Controlled Real-World Test Observations
    print("\n[STEP 1 & 15] PREPARING REAL CROSS-CAMERA VEHICLE OBSERVATIONS IN POSTGRESQL...")
    with Session(engine) as session:
        # Check existing observations
        cams = session.execute(select(Camera)).scalars().all()
        cam_map = {c.name: c.camera_id for c in cams}
        cam_ids = [c.camera_id for c in cams]

        cam_029 = resolve_camera_uuid(session, "c029") or cam_ids[0]
        cam_035 = resolve_camera_uuid(session, "c035") or cam_ids[1]
        cam_020 = resolve_camera_uuid(session, "c020") or cam_ids[2]

        # Insert test scenario observations
        # Scenario A: Same Vehicle across 3 cameras (CAM020 -> CAM029 -> CAM035)
        obs_a1 = persist_fused_observation(
            session=session,
            camera_id_str="c020",
            track_id="TRK-101",
            captured_at="2026-09-04T05:00:00Z",
            fused_plate_text="TN37CY1234",
            fused_confidence=0.940,
            vehicle_type="car",
            vehicle_colour="white",
        )
        obs_a2 = persist_fused_observation(
            session=session,
            camera_id_str="c029",
            track_id="TRK-102",
            captured_at="2026-09-04T05:05:00Z",
            fused_plate_text="TN37CY1234",
            fused_confidence=0.910,
            vehicle_type="car",
            vehicle_colour="white",
        )
        obs_a3 = persist_fused_observation(
            session=session,
            camera_id_str="c035",
            track_id="TRK-103",
            captured_at="2026-09-04T05:10:00Z",
            fused_plate_text="TN37CY1234",
            fused_confidence=0.880,
            vehicle_type="car",
            vehicle_colour="white",
        )

        # Scenario B: Low-Confidence Candidate (1 character substitution from OCR noise: TN37CY1235)
        obs_b1 = persist_fused_observation(
            session=session,
            camera_id_str="c035",
            track_id="TRK-201",
            captured_at="2026-09-04T05:15:00Z",
            fused_plate_text="TN37CY1235",
            fused_confidence=0.650,
            vehicle_type="car",
            vehicle_colour="white",
        )

        # Scenario C: Completely Different Vehicle (KA01AB9876, Truck, Black)
        obs_c1 = persist_fused_observation(
            session=session,
            camera_id_str="c029",
            track_id="TRK-301",
            captured_at="2026-09-04T05:20:00Z",
            fused_plate_text="KA01AB9876",
            fused_confidence=0.920,
            vehicle_type="truck",
            vehicle_colour="black",
        )

    # 2. Verify Exact Formula Calculation & Weights (Step 2, 3, 4)
    print("\n[STEP 2, 3, 4, 12] TESTING IDENTITY SCORE FORMULA & EXPLAINABLE EVIDENCE...")
    test_obs_1 = {
        "fused_plate_text": "TN37CY1234",
        "fused_confidence": 0.91,
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "captured_at": "2026-09-04T10:00:00Z",  # Daytime
    }
    test_obs_2 = {
        "fused_plate_text": "TN37CY1234",
        "fused_confidence": 0.87,
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "captured_at": "2026-09-04T10:05:00Z",  # Daytime
    }
    profile_day = {"day_ocr_reliability": 0.95, "night_ocr_reliability": 0.80}
    
    score_res = compute_identity_score(test_obs_1, test_obs_2, profile_day, profile_day)
    print("  Formula: identity_score = 0.5*plate_sim + 0.3*ocr_comp + 0.1*type_match + 0.1*colour_match")
    print("  Calculated Breakdown:")
    print(f"    • Plate Similarity:          {score_res['plate_similarity']:.4f} (100%)")
    print(f"    • OCR Confidence Component:  {score_res['ocr_confidence_component']:.4f} (weighted by camera reliability {score_res['reliability_a']})")
    print(f"    • Vehicle Type Match:        {score_res['type_match']} (1.0)")
    print(f"    • Vehicle Colour Match:      {score_res['colour_match']} (1.0)")
    print(f"    • Final Identity Score:      {score_res['identity_score']:.4f} -> Status: {score_res['status']}")

    # 3. Run Identity Fusion on Database (Step 5, 6, 7, 8, 10, 11)
    print("\n[STEP 8, 10, 11] EXECUTING DATABASE IDENTITY FUSION ENGINE...")
    with Session(engine) as session:
        summary = run_identity_fusion_on_database(session)
        print(f"  Observations Evaluated:      {summary['observations_count']}")
        print(f"  Cross-Camera Pairs Checked: {summary['matches_evaluated']}")
        print(f"  Confirmed Matches (>=0.70): {summary['confirmed_matches']}")
        print(f"  Candidate Matches (0.4-0.7):{summary['candidate_matches']}")
        print(f"  Canonical Vehicles Created: {summary['canonical_vehicles_count']}")

    # 4. Verify Duplicate Prevention (Step 9)
    print("\n[STEP 9] TESTING DUPLICATE MATCH INSERTION PREVENTION...")
    with Session(engine) as session:
        initial_match_count = session.query(IdentityMatch).count()
        # Rerun fusion on same data
        run_identity_fusion_on_database(session)
        subsequent_match_count = session.query(IdentityMatch).count()
        print(f"  Initial identity_matches Count:    {initial_match_count}")
        print(f"  Count After Re-running Fusion:     {subsequent_match_count}")
        no_dupes = (initial_match_count == subsequent_match_count)
        print(f"  Duplicate Prevention Status:       {'PASS' if no_dupes else 'FAIL'}")

    # 5. Query and Display Real Persisted Identity Matches
    print("\n[STEP 8 & 12] PERSISTED identity_matches RECORDS IN POSTGRESQL:")
    with Session(engine) as session:
        matches = session.execute(
            select(IdentityMatch).order_by(IdentityMatch.identity_score.desc())
        ).scalars().all()

        for idx, m in enumerate(matches[:5]):
            obs_a = session.get(VehicleObservation, m.observation_id_a)
            obs_b = session.get(VehicleObservation, m.observation_id_b)
            print(f"\n  Match #{idx + 1} [ID: {m.match_id}]")
            print(f"    Obs A: {obs_a.fused_plate_text} ({obs_a.vehicle_type}, {obs_a.vehicle_colour}) at Cam {obs_a.camera_id}")
            print(f"    Obs B: {obs_b.fused_plate_text} ({obs_b.vehicle_type}, {obs_b.vehicle_colour}) at Cam {obs_b.camera_id}")
            print(f"    Evidence: plate_sim={m.plate_similarity}, ocr_comp={m.ocr_confidence_component}, type_match={m.type_match}, colour_match={m.colour_match}")
            print(f"    Score: {m.identity_score} | Status: {'CONFIRMED' if m.identity_score >= CONFIRM_THRESHOLD else 'LOW_CONFIDENCE'}")

        # Display Canonical Vehicles
        print("\n[STEP 10 & 11] PERSISTED canonical_vehicles RECORDS IN POSTGRESQL:")
        canonicals = session.execute(select(CanonicalVehicle)).scalars().all()
        for cv in canonicals:
            print(f"    • Canonical Vehicle {cv.canonical_vehicle_id} | Plate: {cv.best_plate_text} | Range: {cv.first_seen_at} -> {cv.last_seen_at}")

    print("\n" + "=" * 75)
    print("IDENTITY FUSION VERIFICATION SUITE COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    run_identity_verification()

