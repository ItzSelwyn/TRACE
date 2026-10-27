"""Diagnostic & Profiling Script for TRACE Hardware, Perception & Pipeline Throughput.
=====================================================================================
Checks hardware allocation (PyTorch CUDA, PaddleOCR, ResNet34), measures latency,
profiles bottlenecks, and benchmarks speed.
"""

import os
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import cv2
import numpy as np
import torch

from app.config import settings

print("=" * 75)
print("  TRACE HARDWARE & ACCELERATION AUDIT")
print("=" * 75)

# 1. PyTorch & CUDA Check
cuda_avail = torch.cuda.is_available()
dev_count = torch.cuda.device_count() if cuda_avail else 0
dev_name = torch.cuda.get_device_name(0) if cuda_avail else "None"
vram_total_mb = (torch.cuda.get_device_properties(0).total_memory / 1024**2) if cuda_avail else 0

print(f"\n[1] PyTorch & CUDA Status:")
print(f"    PyTorch Version:      {torch.__version__}")
print(f"    CUDA Available:       {cuda_avail}")
print(f"    GPU Device Name:      {dev_name}")
print(f"    Total GPU VRAM:       {vram_total_mb:.1f} MB ({vram_total_mb / 1024:.2f} GB)")
print(f"    OpenCV OpenCL Active: {cv2.ocl.useOpenCL()}")

# 2. PaddlePaddle Check
import paddle
paddle_cuda = paddle.device.is_compiled_with_cuda()
paddle_count = paddle.device.cuda.device_count() if hasattr(paddle.device, 'cuda') and paddle_cuda else 0
print(f"\n[2] PaddlePaddle Status:")
print(f"    Paddle Version:       {paddle.__version__}")
print(f"    Compiled with CUDA:   {paddle_cuda}")
print(f"    Paddle Active Device: {'GPU' if paddle_cuda and paddle_count > 0 else 'CPU'}")

# 3. Model Hardware Execution Tests
print(f"\n[3] Model Execution Tests:")

# A. YOLOv8 on dGPU
from ultralytics import YOLO
yolo_path = backend_dir / "models" / "yolov8n.pt"
if not yolo_path.exists():
    yolo_path = backend_dir.parent / "models" / "yolov8n.pt"

yolo_model = YOLO(str(yolo_path))
test_frame = np.zeros((360, 640, 3), dtype=np.uint8)

# Warmup
yolo_model.track(test_frame, device=0 if cuda_avail else "cpu", verbose=False)

# Measure 20 frames
yolo_times = []
for _ in range(20):
    t0 = time.perf_counter()
    yolo_model.track(test_frame, persist=True, tracker="bytetrack.yaml", device=0 if cuda_avail else "cpu", verbose=False)
    yolo_times.append((time.perf_counter() - t0) * 1000.0)

yolo_dev = next(yolo_model.model.parameters()).device
yolo_vram = (torch.cuda.memory_allocated() / 1024**2) if cuda_avail else 0
print(f"    YOLOv8 Device:        {yolo_dev}")
print(f"    YOLOv8 Mean Latency:  {np.mean(yolo_times):.2f} ms ({1000.0 / np.mean(yolo_times):.1f} FPS)")
print(f"    YOLO GPU Memory:      {yolo_vram:.1f} MB allocated")

# B. ResNet34 Appearance Re-ID on dGPU
from app.modules.appearance import get_appearance_extractor
extractor = get_appearance_extractor()
reid_crop = np.zeros((120, 120, 3), dtype=np.uint8)

# Warmup
extractor.extract(reid_crop)

reid_times = []
for _ in range(20):
    t0 = time.perf_counter()
    extractor.extract(reid_crop)
    reid_times.append((time.perf_counter() - t0) * 1000.0)

print(f"    ResNet34 Device:      {extractor.device}")
print(f"    ResNet34 Latency:     {np.mean(reid_times):.2f} ms ({1000.0 / np.mean(reid_times):.1f} crops/sec)")

# C. PaddleOCR on CPU
from app.modules.perception.ocr_engine import read_plate_image
sample_img_path = backend_dir.parent / "data" / "TN" / "TN10.jpg"
if sample_img_path.exists():
    sample_img = cv2.imread(str(sample_img_path))
    
    # Warmup
    read_plate_image(sample_img)
    
    # Single read latency
    ocr_times = []
    for _ in range(5):
        t0 = time.perf_counter()
        read_plate_image(sample_img)
        ocr_times.append((time.perf_counter() - t0) * 1000.0)
    
    print(f"    PaddleOCR Device:     {'GPU' if paddle_cuda else 'CPU'}")
    print(f"    PaddleOCR 1 Read:     {np.mean(ocr_times):.2f} ms")
    print(f"    Estimated 5 Variants: {np.mean(ocr_times) * 5:.2f} ms (sequential on CPU)")

print("\n" + "=" * 75)
print("  PROFILING SUMMARY & BOTTLENECK ANALYSIS")
print("=" * 75)
print(f"  • YOLOv8 Detection:  Runs on {yolo_dev} (Fast: ~{np.mean(yolo_times):.1f}ms per frame)")
print(f"  • ResNet34 Re-ID:    Runs on {extractor.device} (Fast: ~{np.mean(reid_times):.1f}ms per crop)")
print(f"  • PaddleOCR:         Runs on {'GPU' if paddle_cuda else 'CPU'} (Heavy: ~{np.mean(ocr_times):.1f}ms per call)")
print("=" * 75)

