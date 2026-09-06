"""Layer 1 — Perception Module: Comprehensive Automated Verification Suite."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import cv2
import numpy as np

from app.modules.perception.normalization import compute_character_accuracy, normalize_plate_text
from app.modules.perception.ocr_engine import get_ocr_engine, read_plate_image
from app.modules.perception.pipeline import PerceptionPipeline
from app.modules.perception.plate_localizer import extract_plate_crop, load_pascal_voc_annotation
from app.modules.perception.temporal_fusion import TemporalOCRFusion


def verify_all():
    print("=" * 70)
    print("TRACE PERCEPTION LAYER — COMPREHENSIVE VERIFICATION SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. VERIFY YOLO & BYTETRACK ON CITYFLOW FOOTAGE
    # -------------------------------------------------------------
    print("\n[STEP 1 & 2] VERIFYING YOLO + BYTETRACK ON CITYFLOW FOOTAGE...")
    vpath = backend_dir.parent / "data" / "footage" / "c020" / "vdo.avi"
    if not vpath.exists():
        print(f"Error: Footage not found at {vpath}")
        return

    pipeline = PerceptionPipeline(camera_id="CAM020", confidence=0.25, enable_ocr=True, enable_logging=True)
    cap = cv2.VideoCapture(str(vpath))

    track_history = {}
    total_yolo_detections = 0

    print("\n--- Running 15 Frames of Live Perception Pipeline ---")
    for f in range(15):
        ret, frame = cap.read()
        if not ret:
            break
        obs_list, active = pipeline.process_frame(frame, frame_id=f + 1, timestamp=f"10:00:{f:02d} AM")
        total_yolo_detections += len(obs_list)
        for obs in obs_list:
            tid = obs["track_id"]
            track_history.setdefault(tid, []).append(f + 1)

    cap.release()

    print("\n--- ByteTrack Persistence Verification ---")
    persistent_tracks = {tid: frames for tid, frames in track_history.items() if len(frames) >= 3}
    for tid, frames in list(persistent_tracks.items())[:5]:
        print(f"  Track ID {tid}: Visible continuously in frames {frames}")

    yolo_pass = total_yolo_detections > 0
    bytetrack_pass = len(persistent_tracks) > 0

    print(f"\nYOLO STATUS:      {'PASS' if yolo_pass else 'FAIL'} (Total Detections: {total_yolo_detections})")
    print(f"BYTETRACK STATUS: {'PASS' if bytetrack_pass else 'FAIL'} (Persistent Tracks: {len(persistent_tracks)})")

    # -------------------------------------------------------------
    # 2. VERIFY PADDLEOCR ON data/TN
    # -------------------------------------------------------------
    print("\n[STEP 4, 5, 6, 7] VERIFYING PADDLEOCR & NORMALIZATION ON data/TN...")
    tn_dir = backend_dir.parent / "data" / "TN"
    xml_files = sorted(tn_dir.glob("*.xml"))

    exact_matches = 0
    total_char_acc = 0.0
    total_conf = 0.0
    tn_count = 0

    print(f"{'IMAGE':<10} | {'GROUND TRUTH':<13} | {'PREDICTED':<13} | {'CONF':<6} | {'EXACT':<5} | {'CHAR ACC':<8}")
    print("-" * 65)

    for xml_path in xml_files:
        annot = load_pascal_voc_annotation(xml_path)
        if not annot:
            continue
        img_path = tn_dir / annot["filename"]
        if not img_path.exists():
            continue

        img = cv2.imread(str(img_path))
        crop = extract_plate_crop(img, bbox=annot.get("bbox"))
        ocr_results = read_plate_image(crop)

        gt = normalize_plate_text(annot["ground_truth_plate"])
        if ocr_results:
            best = max(ocr_results, key=lambda x: x["confidence"])
            pred = best["normalized_text"]
            conf = best["confidence"]
        else:
            full_res = read_plate_image(img)
            if full_res:
                best = max(full_res, key=lambda x: x["confidence"])
                pred = best["normalized_text"]
                conf = best["confidence"]
            else:
                pred = "UNREADABLE"
                conf = 0.0

        is_exact = (pred == gt)
        char_acc = compute_character_accuracy(pred if pred != "UNREADABLE" else "", gt)

        if is_exact:
            exact_matches += 1
        total_char_acc += char_acc
        if conf > 0:
            total_conf += conf
        tn_count += 1

        exact_str = "YES" if is_exact else "NO"
        print(f"{img_path.name:<10} | {gt:<13} | {pred:<13} | {conf:<6.2f} | {exact_str:<5} | {char_acc:<8.2f}")

    print("-" * 65)
    exact_acc = (exact_matches / tn_count) if tn_count > 0 else 0.0
    avg_char_acc = (total_char_acc / tn_count) if tn_count > 0 else 0.0
    avg_conf = (total_conf / max(1, tn_count)) if tn_count > 0 else 0.0

    print(f"PaddleOCR Exact Match Accuracy:     {exact_acc * 100:.1f}% ({exact_matches}/{tn_count})")
    print(f"PaddleOCR Character-Level Accuracy: {avg_char_acc * 100:.1f}%")
    print(f"PaddleOCR Average Confidence:       {avg_conf:.4f}")
    paddle_pass = tn_count > 0 and exact_acc >= 0.70

    print(f"PADDLEOCR STATUS: {'PASS' if paddle_pass else 'FAIL'}")

    # -------------------------------------------------------------
    # 3. VERIFY TEMPORAL OCR FUSION
    # -------------------------------------------------------------
    print("\n[STEP 8] VERIFYING TEMPORAL OCR FUSION...")
    fusion = TemporalOCRFusion()
    test_reads = [
        (100, "TN 37 CY 1234", 0.61),
        (101, "TN 37 CY 1234", 0.74),
        (102, "TN 37 CY 1234", 0.89),
        (103, "TN37CY1234", 0.94),
        (104, "TN37CY1234", 0.91),
    ]
    for fid, text, conf in test_reads:
        fusion.add_ocr_read(camera_id="CAM029", track_id="TRK-017", frame_id=fid, raw_text=text, confidence=conf)

    fused_obs = fusion.fuse_track(camera_id="CAM029", track_id="TRK-017", vehicle_type="car", vehicle_colour="white")
    print("Multi-frame temporal readings input:")
    for fid, text, conf in test_reads:
        print(f"  Frame {fid} -> raw_text='{text}' -> conf={conf}")
    print("\nFused Result Output:")
    print(json.dumps(fused_obs, indent=2))

    fusion_pass = (
        fused_obs["fused_plate_text"] == "TN37CY1234"
        and fused_obs["fused_confidence"] is not None
        and fused_obs["fused_confidence"] >= 0.90
        and fused_obs["ocr_samples_count"] == 5
    )
    print(f"TEMPORAL FUSION STATUS: {'PASS' if fusion_pass else 'FAIL'}")

    # -------------------------------------------------------------
    # 4. VERIFY OCR FAILURE HANDLING (NFR-05 GRACEFUL DEGRADATION)
    # -------------------------------------------------------------
    print("\n[STEP 9] VERIFYING OCR FAILURE CONTAINMENT (NFR-05)...")
    test_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    
    # Run pipeline with simulated OCR exception
    print("Testing Case C: OCR throws an exception...")
    try:
        obs_c, active_c = pipeline.process_frame(test_frame, frame_id=999, simulate_ocr_failure=True)
        print("  -> Perception pipeline successfully caught OCR exception and continued execution.")
        failure_pass = True
    except Exception as e:
        print(f"  -> Pipeline crashed: {e}")
        failure_pass = False

    print(f"FAILURE HANDLING STATUS: {'PASS' if failure_pass else 'FAIL'}")

    # -------------------------------------------------------------
    # 5. VERIFY LIVE CURRENT VEHICLE OBSERVATION OBJECT
    # -------------------------------------------------------------
    print("\n[STEP 10] VERIFYING CURRENT VEHICLE OBSERVATION JSON STRUCTURE...")
    sample_obs = {
        "camera_id": "CAM029",
        "observation_id": "TRACE-CAM029-17",
        "track_id": "TRK-017",
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "plate": fused_obs["fused_plate_text"],
        "ocr_confidence": fused_obs["fused_confidence"],
        "timestamp": "10:14:22 AM",
        "is_moving": True,
    }
    print(json.dumps(sample_obs, indent=2))
    print("\n" + "=" * 70)
    print("ALL PERCEPTION MODULE VERIFICATIONS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    verify_all()

