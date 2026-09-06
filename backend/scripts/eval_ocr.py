"""Layer 1 — Perception Module: Standalone OCR Evaluation Script on data/TN dataset."""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import cv2

from app.modules.perception.normalization import compute_character_accuracy, normalize_plate_text
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.plate_localizer import extract_plate_crop, load_pascal_voc_annotation


def run_ocr_evaluation(dataset_dir: Path | str | None = None) -> dict:
    """Run PaddleOCR on all images in data/TN and compute evaluation metrics."""
    if dataset_dir is None:
        dataset_dir = backend_dir.parent / "data" / "TN"
    else:
        dataset_dir = Path(dataset_dir)

    if not dataset_dir.exists():
        print(f"Dataset directory not found: {dataset_dir}")
        return {}

    xml_files = sorted(dataset_dir.glob("*.xml"))
    jpg_files = sorted(dataset_dir.glob("*.jpg"))

    print(f"\n=======================================================")
    print(f"TRACE PERCEPTION LAYER — PADDLEOCR EVALUATION REPORT")
    print(f"Dataset Path: {dataset_dir}")
    print(f"Total Samples Found: {len(xml_files)} XML annotations, {len(jpg_files)} Images")
    print(f"=======================================================\n")

    header = f"{'IMAGE':<12} | {'GROUND TRUTH':<14} | {'PREDICTED':<14} | {'CONF':<6} | {'EXACT':<5} | {'CHAR ACC':<8}"
    print(header)
    print("-" * len(header))

    results_table = []
    exact_matches = 0
    total_char_acc = 0.0
    total_conf = 0.0
    count = 0

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

        # 1. First attempt: Plate Crop based on Bounding Box
        crop = extract_plate_crop(img, bbox=annot.get("bbox"))
        ocr_results = read_plate_image(crop)

        # 2. Fallback: Full Image
        if not ocr_results:
            ocr_results = read_plate_image(img)

        if ocr_results:
            best = max(ocr_results, key=lambda x: x["confidence"])
            pred = best["normalized_text"]
            raw_pred = best["raw_text"]
            conf = best["confidence"]
        else:
            pred = "UNREADABLE"
            raw_pred = ""
            conf = 0.0

        is_exact = (pred == gt) if gt else False
        char_acc = compute_character_accuracy(pred if pred != "UNREADABLE" else "", gt) if gt else 0.0

        if is_exact:
            exact_matches += 1
        total_char_acc += char_acc
        if conf > 0:
            total_conf += conf
        count += 1

        exact_str = "YES" if is_exact else "NO"
        print(f"{img_path.name:<12} | {gt:<14} | {pred:<14} | {conf:<6.2f} | {exact_str:<5} | {char_acc:<8.2f}")

        results_table.append({
            "image": img_path.name,
            "ground_truth": gt,
            "predicted": pred,
            "raw_text": raw_pred,
            "confidence": conf,
            "exact_match": is_exact,
            "char_acc": char_acc,
        })

    print("-" * len(header))
    exact_acc = (exact_matches / count) if count > 0 else 0.0
    avg_char_acc = (total_char_acc / count) if count > 0 else 0.0
    avg_conf = (total_conf / max(1, count)) if count > 0 else 0.0

    print(f"Total Images Evaluated:     {count}")
    print(f"Exact-Match Accuracy:       {exact_acc * 100:.1f}% ({exact_matches}/{count})")
    print(f"Character-Level Accuracy:   {avg_char_acc * 100:.1f}%")
    print(f"Average OCR Confidence:     {avg_conf:.4f}")
    print(f"=======================================================\n")

    return {
        "count": count,
        "exact_matches": exact_matches,
        "exact_match_accuracy": exact_acc,
        "average_char_accuracy": avg_char_acc,
        "average_confidence": avg_conf,
        "results": results_table,
    }


if __name__ == "__main__":
    run_ocr_evaluation()

