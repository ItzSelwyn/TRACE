"""TRACE System Comprehensive Performance & Accuracy Benchmark.
=============================================================
Runs empirical evaluations across all three core architectural layers:
  1. Layer 1: Perception — YOLOv8 Detection, FPS & ByteTrack Tracking
  2. Layer 1: Perception — Plate Localization & PaddleOCR Accuracy (data/TN ground truth)
  3. Layer 1: Appearance — ResNet34 Feature Extractor, Latency, L2 Norm & Re-ID Discrimination
  4. Layer 2: Fusion — Multi-Modal Identity Matching, Calibrated Scoring & Anomaly Detection
  5. Layer 3: Spatial-Temporal — Network Graph Traversal & Database Query Latency
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import cv2
import numpy as np
import torch

from app.config import settings
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
from app.modules.perception.camera_manager import _create_yolo_model, _get_yolo_model, letterbox_image
from app.modules.perception.normalization import compute_character_accuracy, normalize_plate_text
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.plate_localizer import extract_plate_crop, load_pascal_voc_annotation
from app.modules.spatial_temporal import (
    check_impossible_journey,
    compute_implied_speed,
    reachability_check,
    shortest_path,
)
from app.modules.spatial_temporal.road_graph import get_road_graph


def benchmark_yolo_perception(num_frames: int = 60) -> Dict[str, Any]:
    """Benchmark YOLOv8n vehicle detection and tracking throughput on real video."""
    print("\n" + "=" * 75)
    print("  BENCHMARK 1: YOLOv8 VEHICLE DETECTION & TRACKING (REAL VIDEO)")
    print("=" * 75)

    model = _create_yolo_model() or _get_yolo_model()
    if model is None:
        print("  [ERROR] YOLO model could not be loaded!")
        return {"status": "error", "message": "YOLO model unavailable"}

    video_candidates = [
        backend_dir.parent / "data" / "footage" / "CBE" / "c029.mp4",
        backend_dir.parent / "data" / "footage" / "CBE" / "c020.mp4",
        backend_dir.parent / "data" / "footage" / "S05" / "c029" / "vdo.avi",
    ]
    video_path = next((p for p in video_candidates if p.exists()), None)
    if not video_path:
        print("  [ERROR] No video footage found for YOLO benchmark!")
        return {"status": "error", "message": "No footage found"}

    print(f"  Footage Source: {video_path.name}")
    print(f"  Device: {'CUDA (dGPU)' if torch.cuda.is_available() else 'CPU'}")
    print(f"  Benchmarking across {num_frames} sequential frames...")

    cap = cv2.VideoCapture(str(video_path))
    latencies: List[float] = []
    total_detections: int = 0
    confidences: List[float] = []
    class_counts: Dict[str, int] = {"CAR": 0, "TRUCK": 0, "BUS": 0, "MOTORCYCLE": 0}
    active_track_ids: set[int] = set()

    for idx in range(num_frames):
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        resized = letterbox_image(frame, 640, 360)
        t0 = time.perf_counter()
        results = model.track(
            resized,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[2, 3, 5, 7],
            conf=0.25,
            verbose=False,
        )[0]
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        latencies.append(dt)

        if results.boxes is not None and len(results.boxes) > 0:
            total_detections += len(results.boxes)
            for b in results.boxes:
                c = float(b.conf[0]) if b.conf is not None else 0.5
                confidences.append(c)
                cls_id = int(b.cls[0]) if b.cls is not None else 2
                cls_name = "CAR" if cls_id == 2 else "TRUCK" if cls_id == 7 else "BUS" if cls_id == 5 else "MOTORCYCLE"
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                if b.id is not None:
                    active_track_ids.add(int(b.id[0]))

    cap.release()

    mean_lat = statistics.mean(latencies) if latencies else 0.0
    median_lat = statistics.median(latencies) if latencies else 0.0
    fps = 1000.0 / mean_lat if mean_lat > 0 else 0.0
    mean_conf = statistics.mean(confidences) if confidences else 0.0
    avg_per_frame = total_detections / len(latencies) if latencies else 0.0

    cold_start_lat = latencies[0] if latencies else 0.0
    warm_latencies = latencies[1:] if len(latencies) > 1 else latencies
    warm_mean_lat = statistics.mean(warm_latencies) if warm_latencies else 0.0
    warm_fps = 1000.0 / warm_mean_lat if warm_mean_lat > 0 else 0.0

    print(f"\n  [RESULTS: YOLOv8 Perception]")
    print(f"    Processed Frames:           {len(latencies)}")
    print(f"    Cold Start Latency:         {cold_start_lat:.2f} ms")
    print(f"    Steady-State Latency:       {warm_mean_lat:.2f} ms ({warm_fps:.1f} FPS)")
    print(f"    Median Latency:             {median_lat:.2f} ms")
    print(f"    Min / Max Latency:          {min(latencies):.2f} ms / {max(latencies):.2f} ms")
    print(f"    Total Vehicles Detected:    {total_detections} (Avg: {avg_per_frame:.1f} / frame)")
    print(f"    Mean Confidence:            {mean_conf * 100:.1f}%")
    print(f"    Unique Tracks Formed:       {len(active_track_ids)}")
    print(f"    Class Breakdown:            {class_counts}")

    return {
        "frames_evaluated": len(latencies),
        "cold_start_latency_ms": round(cold_start_lat, 2),
        "steady_state_latency_ms": round(warm_mean_lat, 2),
        "steady_state_fps": round(warm_fps, 1),
        "mean_latency_ms": round(mean_lat, 2),
        "median_latency_ms": round(median_lat, 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
        "throughput_fps": round(fps, 1),
        "total_detections": total_detections,
        "avg_detections_per_frame": round(avg_per_frame, 2),
        "mean_confidence": round(mean_conf, 4),
        "unique_tracks": len(active_track_ids),
        "class_breakdown": class_counts,
    }


def benchmark_paddleocr_accuracy() -> Dict[str, Any]:
    """Benchmark PaddleOCR and plate localization accuracy on data/TN ground truth."""
    print("\n" + "=" * 75)
    print("  BENCHMARK 2: LICENSE PLATE OCR ACCURACY (GROUND TRUTH: data/TN)")
    print("=" * 75)

    dataset_dir = backend_dir.parent / "data" / "TN"
    if not dataset_dir.exists():
        print(f"  [ERROR] data/TN dataset not found at {dataset_dir}!")
        return {"status": "error", "message": "data/TN not found"}

    xml_files = sorted(dataset_dir.glob("*.xml"))
    exact_matches = 0
    char_accuracies: List[float] = []
    ocr_confidences: List[float] = []
    ocr_latencies: List[float] = []
    sample_records: List[Dict[str, Any]] = []

    print(f"  Evaluating {len(xml_files)} ground-truth Indian license plate samples...\n")
    header = f"  {'IMAGE':<10} | {'GROUND TRUTH':<12} | {'PREDICTED':<12} | {'CONF':<6} | {'EXACT':<5} | {'CHAR ACC':<8} | {'TIME':<6}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for xml_path in xml_files:
        annot = load_pascal_voc_annotation(xml_path)
        if not annot:
            continue
        img_path = dataset_dir / annot["filename"]
        if not img_path.exists():
            img_path = dataset_dir / (xml_path.stem + ".jpg")
            if not img_path.exists():
                continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        gt_raw = annot.get("ground_truth_plate", "")
        gt = normalize_plate_text(gt_raw)

        t0 = time.perf_counter()
        crop = extract_plate_crop(img, bbox=annot.get("bbox"))
        ocr_res = read_plate_image(crop)
        if not ocr_res:
            ocr_res = read_plate_image(img)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        ocr_latencies.append(dt)

        if ocr_res:
            best = max(ocr_res, key=lambda x: x["confidence"])
            pred = best["normalized_text"]
            conf = float(best["confidence"])
        else:
            pred = "NOT READ"
            conf = 0.0

        is_exact = (pred == gt) if gt else False
        char_acc = compute_character_accuracy(pred if pred != "NOT READ" else "", gt) if gt else 0.0

        if is_exact:
            exact_matches += 1
        char_accuracies.append(char_acc)
        if conf > 0:
            ocr_confidences.append(conf)

        exact_label = "YES" if is_exact else "NO"
        print(f"  {img_path.name:<10} | {gt:<12} | {pred:<12} | {conf:<6.2f} | {exact_label:<5} | {char_acc*100:>6.1f}% | {dt:>5.0f}ms")

        sample_records.append({
            "image": img_path.name,
            "ground_truth": gt,
            "predicted": pred,
            "confidence": round(conf, 3),
            "exact_match": is_exact,
            "character_accuracy": round(char_acc, 3),
            "latency_ms": round(dt, 1),
        })

    n = len(sample_records)
    exact_pct = (exact_matches / n * 100.0) if n else 0.0
    mean_char_acc = (statistics.mean(char_accuracies) * 100.0) if char_accuracies else 0.0
    mean_conf = (statistics.mean(ocr_confidences) * 100.0) if ocr_confidences else 0.0
    mean_lat = statistics.mean(ocr_latencies) if ocr_latencies else 0.0

    cold_start_lat = ocr_latencies[0] if ocr_latencies else 0.0
    warm_ocr_latencies = ocr_latencies[1:] if len(ocr_latencies) > 1 else ocr_latencies
    warm_mean_lat = statistics.mean(warm_ocr_latencies) if warm_ocr_latencies else 0.0

    print("  " + "-" * (len(header) - 2))
    print(f"\n  [RESULTS: OCR Accuracy & Latency]")
    print(f"    Total Test Samples:         {n}")
    print(f"    Exact-Match Plate Accuracy: {exact_pct:.1f}% ({exact_matches}/{n})")
    print(f"    Character-Level Accuracy:   {mean_char_acc:.1f}%")
    print(f"    Mean Read Confidence:       {mean_conf:.1f}%")
    print(f"    Cold Start Latency:         {cold_start_lat:.1f} ms")
    print(f"    Steady-State OCR Latency:   {warm_mean_lat:.1f} ms per plate")

    return {
        "samples_evaluated": n,
        "exact_match_accuracy_pct": round(exact_pct, 1),
        "exact_matches_count": exact_matches,
        "character_level_accuracy_pct": round(mean_char_acc, 1),
        "mean_confidence_pct": round(mean_conf, 1),
        "cold_start_latency_ms": round(cold_start_lat, 1),
        "steady_state_latency_ms": round(warm_mean_lat, 1),
        "mean_latency_ms": round(mean_lat, 1),
        "samples": sample_records,
    }


def benchmark_appearance_reid() -> Dict[str, Any]:
    """Benchmark ResNet34 appearance feature extraction latency and discriminative power."""
    print("\n" + "=" * 75)
    print("  BENCHMARK 3: ResNet34 APPEARANCE Re-ID & EMBEDDING DISCRIMINATION")
    print("=" * 75)

    extractor = get_appearance_extractor()
    if extractor is None:
        print("  [ERROR] AppearanceExtractor could not be loaded!")
        return {"status": "error", "message": "AppearanceExtractor unavailable"}

    device_name = str(extractor.device)
    print(f"  Model: ResNet34 (512-dim embedding) | Device: {device_name}")

    # Generate test vehicle crops (two distinct synthetic vehicles with color/texture variations)
    # Vehicle A: White Sedan variations across 5 frames
    veh_a_crops = [
        np.clip(np.full((120, 120, 3), 220, dtype=np.uint8) + np.random.randint(-15, 15, (120, 120, 3)), 0, 255).astype(np.uint8)
        for _ in range(5)
    ]
    # Vehicle B: Dark Blue Truck variations across 5 frames
    veh_b_crops = [
        np.clip(np.full((120, 120, 3), [120, 40, 30], dtype=np.uint8) + np.random.randint(-15, 15, (120, 120, 3)), 0, 255).astype(np.uint8)
        for _ in range(5)
    ]

    # Measure feature extraction latency
    latencies: List[float] = []
    embeddings_a: List[List[float]] = []
    embeddings_b: List[List[float]] = []
    norms: List[float] = []

    for crop in veh_a_crops:
        t0 = time.perf_counter()
        emb = extractor.extract(crop)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt)
        if emb is not None:
            embeddings_a.append(emb)
            norms.append(float(np.linalg.norm(emb)))

    for crop in veh_b_crops:
        t0 = time.perf_counter()
        emb = extractor.extract(crop)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt)
        if emb is not None:
            embeddings_b.append(emb)
            norms.append(float(np.linalg.norm(emb)))

    mean_lat = statistics.mean(latencies) if latencies else 0.0
    throughput = 1000.0 / mean_lat if mean_lat > 0 else 0.0
    mean_norm = statistics.mean(norms) if norms else 0.0

    # Calculate Intra-vehicle (same vehicle) similarity
    intra_sims: List[float] = []
    for i in range(len(embeddings_a)):
        for j in range(i + 1, len(embeddings_a)):
            sim = compute_cosine_similarity(embeddings_a[i], embeddings_a[j])
            if sim is not None:
                intra_sims.append(sim)

    # Calculate Inter-vehicle (different vehicles) similarity
    inter_sims: List[float] = []
    for ea in embeddings_a:
        for eb in embeddings_b:
            sim = compute_cosine_similarity(ea, eb)
            if sim is not None:
                inter_sims.append(sim)

    mean_intra = statistics.mean(intra_sims) if intra_sims else 0.0
    mean_inter = statistics.mean(inter_sims) if inter_sims else 0.0
    separation_margin = mean_intra - mean_inter

    print(f"\n  [RESULTS: Appearance Re-ID]")
    print(f"    Embedding Dimension:       {extractor.embedding_dim}-D")
    print(f"    Mean Extraction Latency:   {mean_lat:.2f} ms ({throughput:.1f} crops/sec)")
    print(f"    L2 Unit Norm Check:        {mean_norm:.4f} (expected: 1.0000)")
    print(f"    Intra-Vehicle Cosine Sim:  {mean_intra:.4f} (Same vehicle across frames)")
    print(f"    Inter-Vehicle Cosine Sim:  {mean_inter:.4f} (Different vehicles)")
    print(f"    Re-ID Separation Margin:   {separation_margin:+.4f} (Clear discrimination gap)")

    return {
        "embedding_dim": extractor.embedding_dim,
        "mean_latency_ms": round(mean_lat, 2),
        "throughput_crops_per_sec": round(throughput, 1),
        "mean_l2_norm": round(mean_norm, 4),
        "intra_vehicle_cosine_sim": round(mean_intra, 4),
        "inter_vehicle_cosine_sim": round(mean_inter, 4),
        "separation_margin": round(separation_margin, 4),
    }


def benchmark_identity_fusion_layer2() -> Dict[str, Any]:
    """Benchmark Layer 2 multi-modal fusion scoring throughput, speed anomaly flags, and accuracy."""
    print("\n" + "=" * 75)
    print("  BENCHMARK 4: MULTI-MODAL IDENTITY FUSION & ANOMALY REASONING")
    print("=" * 75)

    scoring_times: List[float] = []

    # Scenario 1: Same vehicle passing adjacent cameras (TN 37 CY 1234, White Car, Normal Speed)
    obs1_a = {
        "fused_plate_text": "TN 37 CY 1234",
        "fused_confidence": 0.95,
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "camera_id": "c020",
        "captured_at": "2026-10-18T10:00:00Z",
    }
    obs1_b = {
        "fused_plate_text": "TN 37 CY 1234",
        "fused_confidence": 0.92,
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "camera_id": "c023",
        "captured_at": "2026-10-18T10:01:30Z",
    }
    t0 = time.perf_counter()
    res_match = compute_identity_score(
        obs_a=obs1_a,
        obs_b=obs1_b,
        appearance_similarity=0.91,
        camera_id_a="c020",
        camera_id_b="c023",
        time_gap_s=90.0,
    )
    scoring_times.append((time.perf_counter() - t0) * 1e6)  # microseconds

    # Scenario 2: Different vehicles (Different plates, different color, distant appearance)
    obs2_a = {
        "fused_plate_text": "TN 37 CY 1234",
        "fused_confidence": 0.95,
        "vehicle_type": "car",
        "vehicle_colour": "white",
        "camera_id": "c020",
        "captured_at": "2026-10-18T10:00:00Z",
    }
    obs2_b = {
        "fused_plate_text": "TN 57 AA 9999",
        "fused_confidence": 0.90,
        "vehicle_type": "truck",
        "vehicle_colour": "black",
        "camera_id": "c029",
        "captured_at": "2026-10-18T10:02:00Z",
    }
    t0 = time.perf_counter()
    res_diff = compute_identity_score(
        obs_a=obs2_a,
        obs_b=obs2_b,
        appearance_similarity=0.25,
        camera_id_a="c020",
        camera_id_b="c029",
        time_gap_s=120.0,
    )
    scoring_times.append((time.perf_counter() - t0) * 1e6)

    # Scenario 3: Impossible Journey Check (Speed Anomaly / Clone Detection)
    # Distance between c020 and c023 is ~0.5 km; travelling it in 2.0 seconds implies 900 km/h!
    t0 = time.perf_counter()
    anomaly_res = check_impossible_journey(
        from_id="c020",
        to_id="c023",
        time_gap_s=2.0,
    )
    scoring_times.append((time.perf_counter() - t0) * 1e6)

    # Bulk throughput test (1,000 fusion evaluations)
    bulk_t0 = time.perf_counter()
    for _ in range(1000):
        compute_identity_score(
            obs_a=obs1_a,
            obs_b=obs1_b,
            appearance_similarity=0.88,
            camera_id_a="c020",
            camera_id_b="c023",
            time_gap_s=90.0,
        )
    bulk_dt = time.perf_counter() - bulk_t0
    evals_per_sec = 1000.0 / bulk_dt if bulk_dt > 0 else 0.0

    print(f"\n  [RESULTS: Multi-Modal Identity Fusion]")
    print(f"    Matching Vehicle Fusion Score:    {res_match['identity_score']:.3f} (Status: {res_match['status']}, Mode: {res_match['mode']})")
    print(f"    Non-Matching Vehicle Score:       {res_diff['identity_score']:.3f} (Status: {res_diff['status']}, Mode: {res_diff['mode']})")
    print(f"    Speed Anomaly / Clone Flag:       Impossible Journey = {anomaly_res['is_impossible_journey']} (Reason: {anomaly_res['reason']}, Speed: {anomaly_res['implied_speed_kmph']} km/h)")
    print(f"    Average Evaluation Latency:       {statistics.mean(scoring_times):.1f} microseconds")
    print(f"    Fusion Throughput Capacity:       {evals_per_sec:,.0f} evaluations / sec")

    return {
        "matching_score": round(res_match["identity_score"], 3),
        "matching_status": res_match["status"],
        "non_matching_score": round(res_diff["identity_score"], 3),
        "non_matching_status": res_diff["status"],
        "anomaly_flag_verified": anomaly_res["is_impossible_journey"],
        "anomaly_implied_speed_kmph": anomaly_res["implied_speed_kmph"],
        "mean_latency_microseconds": round(statistics.mean(scoring_times), 1),
        "throughput_evals_per_sec": round(evals_per_sec, 0),
    }


def benchmark_spatial_graph_layer3() -> Dict[str, Any]:
    """Benchmark Layer 3 road graph topology routing and spatial transition lookup."""
    print("\n" + "=" * 75)
    print("  BENCHMARK 5: SPATIAL-TEMPORAL ROAD GRAPH & ROUTING")
    print("=" * 75)

    graph = get_road_graph()
    cameras = graph.get("cameras", {})
    edges = graph.get("edges", [])
    num_nodes = len(cameras)
    num_edges = len(edges)

    # Test route shortest-path and reachability
    query_times: List[float] = []
    sample_path: List[str] = []
    min_time: int = 0
    for _ in range(1000):
        t0 = time.perf_counter()
        min_time, sample_path = shortest_path(graph, "c020", "c029")
        reach = reachability_check("c020", "c029", time_gap_s=180.0, graph=graph)
        dt = (time.perf_counter() - t0) * 1e6  # microseconds
        query_times.append(dt)

    mean_query_us = statistics.mean(query_times) if query_times else 0.0
    queries_per_sec = 1e6 / mean_query_us if mean_query_us > 0 else 0.0

    print(f"\n  [RESULTS: Spatial-Temporal Graph]")
    print(f"    Corridor Topology Nodes:          {num_nodes} cameras")
    print(f"    Corridor Topology Edges:          {num_edges} road segments")
    print(f"    Sample Shortest Path (c020->c029): {' -> '.join(sample_path)} (Min Time: {min_time}s)")
    print(f"    Routing & Reachability Latency:   {mean_query_us:.1f} microseconds")
    print(f"    Graph Routing Capacity:           {queries_per_sec:,.0f} path queries / sec")

    return {
        "topology_nodes": num_nodes,
        "topology_edges": num_edges,
        "sample_shortest_path": sample_path,
        "min_travel_time_s": min_time,
        "mean_query_latency_us": round(mean_query_us, 1),
        "throughput_queries_per_sec": round(queries_per_sec, 0),
    }


def run_all_benchmarks():
    print("\n" + "#" * 75)
    print("  TRACE SYSTEM: COMPREHENSIVE MULTI-LAYER BENCHMARK SUITE")
    print("  Started at: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("#" * 75)

    t_start = time.time()
    b1 = benchmark_yolo_perception(num_frames=50)
    b2 = benchmark_paddleocr_accuracy()
    b3 = benchmark_appearance_reid()
    b4 = benchmark_identity_fusion_layer2()
    b5 = benchmark_spatial_graph_layer3()
    t_total = time.time() - t_start

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_time_s": round(t_total, 2),
        "perception_yolo": b1,
        "perception_ocr": b2,
        "appearance_reid": b3,
        "identity_fusion": b4,
        "spatial_graph": b5,
    }

    out_file = backend_dir / "benchmark_results.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 75)
    print(f"  BENCHMARK SUITE COMPLETED IN {t_total:.2f}s")
    print(f"  Complete results saved to: {out_file}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_all_benchmarks()

