import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

import cv2
import numpy as np
from app.modules.perception.camera_manager import _get_yolo_model, letterbox_image
from app.modules.perception.plate_localizer import extract_plate_crop
from app.modules.perception.ocr_engine import read_plate_image

frame = cv2.imread("scratch/frame_1600.jpg")
letterboxed = letterbox_image(frame, 640, 360)

model = _get_yolo_model()
results = model.track(
    letterboxed,
    persist=True,
    tracker="bytetrack.yaml",
    classes=[2, 3, 5, 7],
    conf=0.25,
    verbose=False,
)[0]

print("Boxes count:", len(results.boxes))
for b in results.boxes:
    cls_id = int(b.cls[0])
    conf = float(b.conf[0])
    track_id = int(b.id[0]) if b.id is not None else -1
    bbox = [int(v) for v in b.xyxy[0].tolist()]
    print(f"Track {track_id}, cls={cls_id}, conf={conf:.2f}, bbox={bbox}")
    
    x1, y1, x2, y2 = bbox
    veh_crop = letterboxed[max(0, y1):min(letterboxed.shape[0], y2), max(0, x1):min(letterboxed.shape[1], x2)]
    print(f"veh_crop shape: {veh_crop.shape}")
    cv2.imwrite(f"scratch/crop_trk_{track_id}.jpg", veh_crop)
    
    plate_crop = extract_plate_crop(veh_crop)
    print(f"plate_crop shape: {plate_crop.shape if plate_crop is not None else None}")
    if plate_crop is not None:
        cv2.imwrite(f"scratch/plate_trk_{track_id}.jpg", plate_crop)
        ocr_plate = read_plate_image(plate_crop, min_confidence=0.15)
        print(f"OCR on plate_crop: {ocr_plate}")
    
    ocr_veh = read_plate_image(veh_crop, min_confidence=0.15)
    print(f"OCR on veh_crop: {ocr_veh}")

    # Also test on high-res original frame crop!
    # Map bbox back to original 1920x1080 coordinates
    scale_x = frame.shape[1] / 640.0
    scale_y = frame.shape[0] / 360.0
    orig_x1 = int(x1 * scale_x)
    orig_y1 = int(y1 * scale_y)
    orig_x2 = int(x2 * scale_x)
    orig_y2 = int(y2 * scale_y)
    orig_crop = frame[max(0, orig_y1):min(frame.shape[0], orig_y2), max(0, orig_x1):min(frame.shape[1], orig_x2)]
    cv2.imwrite(f"scratch/orig_crop_trk_{track_id}.jpg", orig_crop)
    orig_plate = extract_plate_crop(orig_crop)
    if orig_plate is not None:
        cv2.imwrite(f"scratch/orig_plate_trk_{track_id}.jpg", orig_plate)
        print(f"OCR on orig_plate: {read_plate_image(orig_plate, min_confidence=0.15)}")
    print(f"OCR on orig_crop: {read_plate_image(orig_crop, min_confidence=0.15)}")
