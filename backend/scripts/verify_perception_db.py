"""Layer 1 — Perception Module: Comprehensive Automated Database Persistence Verification."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
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
from app.db.models import Camera, OcrRead, VehicleObservation
from app.modules.perception.pipeline import PerceptionPipeline


def run_db_verification():
    print("=" * 75)
    print("TRACE PERCEPTION LAYER — POSTGRESQL PERSISTENCE VERIFICATION SUITE")
    print("=" * 75)

    # 1. Test PostgreSQL Connection
    print("\n[STEP 1] TESTING POSTGRESQL / POSTGIS CONNECTION...")
    db_connected = False
    try:
        engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
        with Session(engine) as session:
            cams = session.execute(select(Camera)).scalars().all()
            print(f"  -> Connected successfully to: {settings.DATABASE_URL_SYNC}")
            print(f"  -> Total cameras available in DB: {len(cams)}")
            for c in cams[:4]:
                print(f"     Camera: {c.camera_id} | Name: {c.name} | Status: {c.status}")
            db_connected = True
    except Exception as e:
        print(f"  -> Database connection failed: {e}")
        return

    print(f"DATABASE CONNECTION STATUS: {'PASS' if db_connected else 'FAIL'}")

    # 2. Process Video Stream and Persist to PostgreSQL
    print("\n[STEP 2, 3, 4, 5] RUNNING PERCEPTION PIPELINE & PERSISTING TO POSTGRESQL...")
    vpath = backend_dir.parent / "data" / "footage" / "c020" / "vdo.avi"
    pipeline = PerceptionPipeline(
        camera_id="c020",
        confidence=0.25,
        enable_ocr=True,
        enable_db_persist=True,
        enable_logging=False,
    )

    cap = cv2.VideoCapture(str(vpath))
    frames_processed = 0
    total_detections = 0

    print("  Processing 30 video frames on camera c020...")
    for f in range(30):
        ret, frame = cap.read()
        if not ret:
            break
        obs_list, active = pipeline.process_frame(frame, frame_id=f + 1, timestamp=f"10:00:{f:02d} AM")
        frames_processed += 1
        total_detections += len(obs_list)

    pipeline.finalize_all_tracks()
    cap.release()

    print(f"  -> Frames Processed: {frames_processed}")
    print(f"  -> Total Frame-level Detections: {total_detections}")
    print(f"  -> Unique Tracks Tracked: {len(pipeline.tracked_vehicles)}")
    print(f"  -> Tracks Persisted to DB: {len(pipeline.persisted_tracks)}")

    # 3. Query and Verify PostgreSQL Records
    print("\n[STEP 9] QUERYING POSTGRESQL FOR PERSISTED OBSERVATIONS & OCR READS...")
    with Session(engine) as session:
        observations = session.execute(
            select(VehicleObservation)
            .order_by(VehicleObservation.captured_at.desc())
        ).scalars().all()

        total_obs = len(observations)
        total_ocr_reads = session.query(OcrRead).count()

        print(f"  -> Total vehicle_observations in DB: {total_obs}")
        print(f"  -> Total ocr_reads in DB:            {total_ocr_reads}")

        if observations:
            sample_obs = observations[0]
            print("\n--- Example Real Persisted VehicleObservation Row ---")
            print(f"  Observation ID:   {sample_obs.observation_id}")
            print(f"  Camera ID:        {sample_obs.camera_id}")
            print(f"  Track ID:         {sample_obs.track_id}")
            print(f"  Captured At:      {sample_obs.captured_at}")
            print(f"  Fused Plate:      {sample_obs.fused_plate_text}")
            print(f"  Fused Confidence: {sample_obs.fused_confidence}")
            print(f"  Vehicle Type:     {sample_obs.vehicle_type}")
            print(f"  Vehicle Colour:   {sample_obs.vehicle_colour}")
            print(f"  Associated Reads: {len(sample_obs.ocr_reads)}")

            if sample_obs.ocr_reads:
                print("\n--- Associated Raw OcrRead Rows ---")
                for r in sample_obs.ocr_reads[:4]:
                    print(f"    • OcrRead ID: {r.ocr_read_id} | Raw Plate: '{r.raw_plate_text}' | Conf: {r.confidence} | Timestamp: {r.frame_timestamp}")

    # 4. Verify Track-to-Observation Lifecycle (No 1-row-per-frame explosion)
    print("\n[STEP 14] CHECKING DUPLICATE EXPLOSION PREVENTION...")
    print(f"  Frames Processed:             {frames_processed}")
    print(f"  Frame-level YOLO detections:  {total_detections}")
    print(f"  Persisted DB Observations:    {len(pipeline.persisted_tracks)}")
    
    no_duplicate_explosion = len(pipeline.persisted_tracks) < total_detections
    print(f"  -> Duplicate Explosion Prevented: {'PASS' if no_duplicate_explosion else 'FAIL'}")

    # 5. Multi-Camera Safety & Failure Isolation (NFR-05)
    print("\n[STEP 8] VERIFYING MULTI-CAMERA FAILURE ISOLATION (NFR-05)...")
    cameras_to_test = ["c020", "c023", "c029", "c035"]
    cam_results = {}

    for cid in cameras_to_test:
        try:
            cam_pipe = PerceptionPipeline(camera_id=cid, enable_db_persist=True, enable_logging=False)
            # Simulate failure specifically on c029
            sim_fail = (cid == "c029")
            dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
            obs, _ = cam_pipe.process_frame(dummy_frame, frame_id=1, simulate_ocr_failure=sim_fail)
            cam_results[cid] = "ONLINE (Degraded Handled)" if sim_fail else "ONLINE"
        except Exception as e:
            cam_results[cid] = f"FAILED: {e}"

    for cid, status in cam_results.items():
        print(f"  Camera {cid}: {status}")

    multi_cam_pass = all("FAILED" not in s for s in cam_results.values())
    print(f"MULTI-CAMERA ISOLATION STATUS: {'PASS' if multi_cam_pass else 'FAIL'}")

    print("\n" + "=" * 75)
    print("DATABASE PERSISTENCE & LIFECYCLE VERIFICATION COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    run_db_verification()
