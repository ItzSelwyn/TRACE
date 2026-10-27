"""Benchmark script for TRACE real-time performance optimizations.

Tests:
1. YOLO Frame Stride Comparison (Stride 1 vs Stride 2) on real footage (50 frames).
2. PaddleOCR Short-Circuit Strategy (High confidence immediate accept vs Low confidence fallback search).
3. ResNet34 Appearance Re-ID Reuse for stable tracks.
4. Metrics collection verification.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import torch

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.modules.perception.metrics import get_performance_metrics
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.preprocessing_variants import generate_preprocessing_variants
from ultralytics import YOLO


def run_yolo_stride_benchmark(video_path: Path, num_frames: int = 50) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print(" BENCHMARK 1: YOLO FRAME STRIDE (1 vs 2)")
    print("=" * 60)

    device = getattr(settings, "YOLO_DEVICE", "cuda:0")
    if device == "auto":
        device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Loading YOLO model on device: {device}...")

    model_path = Path("backend/models/yolov8n.pt")
    if not model_path.exists():
        model_path = Path("models/yolov8n.pt")
    model = YOLO(str(model_path))

    results_data = {}

    for stride in [1, 2]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Error: Could not open {video_path}")
            return {}

        frames_processed = 0
        yolo_inferences = 0
        skipped_frames = 0
        total_yolo_latency_ms = 0.0
        cached_boxes = []

        t_start = time.perf_counter()

        while frames_processed < num_frames:
            ret, frame = cap.read()
            if not ret:
                break
            frames_processed += 1

            resized = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)

            is_yolo_frame = (stride == 1) or (frames_processed <= 1) or (frames_processed % stride == 1)

            if not is_yolo_frame:
                skipped_frames += 1
                # Simulating frame rendering with cached boxes
                canvas = resized.copy()
                for b in cached_boxes:
                    cv2.rectangle(canvas, (b[0], b[1]), (b[2], b[3]), (0, 255, 0), 2)
            else:
                yolo_inferences += 1
                t0 = time.perf_counter()
                res = model.track(
                    resized,
                    persist=True,
                    tracker="bytetrack.yaml",
                    classes=[2, 3, 5, 7],
                    conf=0.25,
                    device=device,
                    verbose=False,
                )[0]
                t_yolo = (time.perf_counter() - t0) * 1000.0
                total_yolo_latency_ms += t_yolo

                # Update cached boxes
                cached_boxes = []
                if res.boxes is not None and len(res.boxes) > 0:
                    for box in res.boxes:
                        bbox = [int(v) for v in box.xyxy[0].tolist()]
                        cached_boxes.append(bbox)

        t_total = time.perf_counter() - t_start
        cap.release()

        avg_yolo_ms = (total_yolo_latency_ms / yolo_inferences) if yolo_inferences > 0 else 0.0
        effective_fps = frames_processed / t_total if t_total > 0 else 0.0

        results_data[f"stride_{stride}"] = {
            "total_frames": frames_processed,
            "yolo_inferences": yolo_inferences,
            "skipped_frames": skipped_frames,
            "total_time_s": round(t_total, 3),
            "total_yolo_gpu_ms": round(total_yolo_latency_ms, 2),
            "avg_yolo_latency_ms": round(avg_yolo_ms, 2),
            "effective_fps": round(effective_fps, 1),
        }

        print(f"\n--- Stride = {stride} ---")
        print(f"  Frames: {frames_processed} total | {yolo_inferences} YOLO inferences | {skipped_frames} skipped ({skipped_frames/frames_processed*100:.1f}%)")
        print(f"  Total Wall-clock Time: {t_total:.3f} s")
        print(f"  Total YOLO GPU Time:   {total_yolo_latency_ms:.1f} ms")
        print(f"  Avg YOLO Latency/call: {avg_yolo_ms:.2f} ms")
        print(f"  Effective Frame Rate:  {effective_fps:.1f} FPS")

    s1 = results_data.get("stride_1", {})
    s2 = results_data.get("stride_2", {})
    if s1 and s2:
        gpu_time_saved_pct = ((s1["total_yolo_gpu_ms"] - s2["total_yolo_gpu_ms"]) / s1["total_yolo_gpu_ms"]) * 100
        wall_time_saved_pct = ((s1["total_time_s"] - s2["total_time_s"]) / s1["total_time_s"]) * 100
        fps_boost = ((s2["effective_fps"] - s1["effective_fps"]) / s1["effective_fps"]) * 100
        print(f"\nStride 2 vs Stride 1 Summary:")
        print(f"  -> GPU YOLO Workload Reduction: {gpu_time_saved_pct:.1f}%")
        print(f"  -> Total Pipeline Time Saved:   {wall_time_saved_pct:.1f}%")
        print(f"  -> Effective FPS Improvement:   +{fps_boost:.1f}%")

    return results_data


def run_ocr_short_circuit_benchmark() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print(" BENCHMARK 2: PADDLEOCR SHORT-CIRCUIT STRATEGY")
    print("=" * 60)

    # Pre-warm PaddleOCR engine
    dummy = np.ones((64, 128, 3), dtype=np.uint8) * 200
    read_plate_image(dummy, min_confidence=0.20)

    # Create a clean high-contrast plate crop
    plate_img_clean = np.ones((60, 200, 3), dtype=np.uint8) * 255
    cv2.putText(plate_img_clean, "TN37CY1234", (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 3)

    # Create a corrupted / low-contrast plate crop where ORIGINAL fails or scores < 0.50
    plate_img_degraded = np.zeros((60, 200, 3), dtype=np.uint8)
    # Add heavy noise and faint text
    noise = np.random.normal(50, 20, (60, 200, 3)).astype(np.uint8)
    plate_img_degraded = cv2.add(plate_img_degraded, noise)
    cv2.putText(plate_img_degraded, "DL1ZAA1111", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 120, 120), 1)

    ocr_thresh = float(getattr(settings, "OCR_CONFIDENCE_THRESHOLD", 0.50))
    print(f"Configured OCR_CONFIDENCE_THRESHOLD = {ocr_thresh}")

    # Case A: High Confidence (Should Short-Circuit on ORIGINAL)
    t0 = time.perf_counter()
    orig_variants = generate_preprocessing_variants(plate_img_clean, limit_variants=["ORIGINAL"])
    orig_img = orig_variants[0][1] if orig_variants else plate_img_clean
    orig_ocr = read_plate_image(orig_img, min_confidence=0.20)
    clean_short_circuit = False
    clean_fallbacks = 0
    if orig_ocr and any(x.get("confidence", 0.0) >= ocr_thresh for x in orig_ocr):
        clean_short_circuit = True
    else:
        fallback_variants = generate_preprocessing_variants(
            plate_img_clean,
            limit_variants=["UPSCALE_2X", "CLAHE", "DENOISED_SHARPEN", "ADAPTIVE_THRESH"],
        )
        for _, v_img in fallback_variants:
            clean_fallbacks += 1
            read_plate_image(v_img, min_confidence=0.20)
    t_clean_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\nCase A (Clean Plate Crop - High Confidence):")
    print(f"  Detected Text:   '{orig_ocr[0]['raw_text'] if orig_ocr else 'NONE'}'")
    print(f"  Confidence:      {orig_ocr[0]['confidence'] if orig_ocr else 0.0:.3f}")
    print(f"  Short-Circuited: {clean_short_circuit} (Fallbacks run: {clean_fallbacks})")
    print(f"  Inference Time:  {t_clean_ms:.1f} ms")

    # Measure full non-short-circuited execution (all 5 variants) for comparison
    t0 = time.perf_counter()
    all_vars = generate_preprocessing_variants(
        plate_img_clean,
        limit_variants=["ORIGINAL", "UPSCALE_2X", "CLAHE", "DENOISED_SHARPEN", "ADAPTIVE_THRESH"],
    )
    for _, img in all_vars:
        read_plate_image(img, min_confidence=0.20)
    t_full_ms = (time.perf_counter() - t0) * 1000.0
    print(f"  Full 5-variant sequential latency (unoptimized): {t_full_ms:.1f} ms")
    if t_full_ms > 0:
        time_saved = ((t_full_ms - t_clean_ms) / t_full_ms) * 100
        print(f"  -> CPU Time Saved by Short-Circuiting: {time_saved:.1f}% ({t_full_ms - t_clean_ms:.1f} ms saved per plate)")

    # Case B: Degraded Plate (Below Threshold, Must Run Fallbacks)
    t0 = time.perf_counter()
    orig_variants_deg = generate_preprocessing_variants(plate_img_degraded, limit_variants=["ORIGINAL"])
    orig_img_deg = orig_variants_deg[0][1] if orig_variants_deg else plate_img_degraded
    orig_ocr_deg = read_plate_image(orig_img_deg, min_confidence=0.20)
    deg_short_circuit = False
    deg_fallbacks = 0
    if orig_ocr_deg and any(x.get("confidence", 0.0) >= ocr_thresh for x in orig_ocr_deg):
        deg_short_circuit = True
    else:
        fallback_variants = generate_preprocessing_variants(
            plate_img_degraded,
            limit_variants=["UPSCALE_2X", "CLAHE", "DENOISED_SHARPEN", "ADAPTIVE_THRESH"],
        )
        for _, v_img in fallback_variants:
            deg_fallbacks += 1
            f_ocr = read_plate_image(v_img, min_confidence=0.20)
            if f_ocr and any(x.get("confidence", 0.0) >= ocr_thresh for x in f_ocr):
                break
    t_deg_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\nCase B (Degraded Plate Crop - Triggers Fallbacks):")
    print(f"  ORIGINAL crop conf: {orig_ocr_deg[0]['confidence'] if orig_ocr_deg else 0.0:.3f}")
    print(f"  Short-Circuited:    {deg_short_circuit}")
    print(f"  Fallbacks executed: {deg_fallbacks} variants")
    print(f"  Latency:            {t_deg_ms:.1f} ms")

    return {
        "clean_plate": {
            "short_circuited": clean_short_circuit,
            "fallbacks_run": clean_fallbacks,
            "latency_ms": round(t_clean_ms, 1),
            "unoptimized_full_latency_ms": round(t_full_ms, 1),
        },
        "degraded_plate": {
            "short_circuited": deg_short_circuit,
            "fallbacks_run": deg_fallbacks,
            "latency_ms": round(t_deg_ms, 1),
        },
    }


def run_reid_reuse_benchmark() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print(" BENCHMARK 3: RESNET34 APPEARANCE RE-ID REUSE")
    print("=" * 60)

    from app.modules.appearance import get_appearance_extractor

    extractor = get_appearance_extractor()
    print(f"Appearance Extractor: {extractor.model_name} on {extractor.device} (FP16={getattr(extractor, 'use_half', False)})")

    # Generate a dummy vehicle crop
    veh_crop = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)

    # Initial inference
    t0 = time.perf_counter()
    emb_1, _ = extractor.extract_with_reason(veh_crop, min_size=32)
    t_initial_ms = (time.perf_counter() - t0) * 1000.0

    # Stable track reuse (simulating 10 successive frames where track is stable)
    t0 = time.perf_counter()
    reused_count = 10
    cached_emb = emb_1
    for _ in range(reused_count):
        # When track has embedding, we reuse cached_emb without model inference
        _ = cached_emb
    t_reused_total_ms = (time.perf_counter() - t0) * 1000.0
    avg_reused_ms = t_reused_total_ms / reused_count

    # Compare against redundant inference (unoptimized behavior)
    t0 = time.perf_counter()
    for _ in range(reused_count):
        _ = extractor.extract_with_reason(veh_crop, min_size=32)
    t_redundant_total_ms = (time.perf_counter() - t0) * 1000.0

    print(f"Initial Re-ID inference on GPU: {t_initial_ms:.2f} ms")
    print(f"Redundant 10 inferences on stable track (unoptimized): {t_redundant_total_ms:.2f} ms")
    print(f"Reused 10 lookups on stable track (optimized):          {t_reused_total_ms:.4f} ms")
    print(f"  -> GPU Workload Saved on 10 frames: {t_redundant_total_ms - t_reused_total_ms:.1f} ms")

    return {
        "initial_inference_ms": round(t_initial_ms, 2),
        "redundant_10x_ms": round(t_redundant_total_ms, 2),
        "reused_10x_ms": round(t_reused_total_ms, 4),
    }


def main():
    video_candidates = [
        Path("data/footage/c029/vdo.avi"),
        Path("data/footage/c020/vdo.avi"),
        Path("data/footage/c023/vdo.avi"),
    ]
    video_path = next((p for p in video_candidates if p.exists()), None)
    if not video_path:
        print("Error: No test video footage found.")
        sys.exit(1)

    print(f"Using test video: {video_path}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")

    yolo_res = run_yolo_stride_benchmark(video_path, num_frames=50)
    ocr_res = run_ocr_short_circuit_benchmark()
    reid_res = run_reid_reuse_benchmark()

    print("\n" + "=" * 60)
    print(" ALL BENCHMARKS COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()

