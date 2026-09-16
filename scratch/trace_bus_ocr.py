import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

import cv2
from app.modules.perception.camera_manager import _get_yolo_model, letterbox_image
from app.modules.perception.plate_localizer import extract_plate_crop
from app.modules.perception.ocr_engine import read_plate_image
from app.modules.perception.normalization import normalize_plate_text

cap = cv2.VideoCapture("data/footage/CBE/3.MOV")
model = _get_yolo_model()

print("Testing first 100 frames of 3.MOV for bus detections...")
for fidx in range(0, 100, 5):
    cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
    ret, frame = cap.read()
    if not ret:
        break
    letterboxed = letterbox_image(frame, 640, 360)
    results = model.track(
        letterboxed,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[2, 3, 5, 7],
        conf=0.25,
        verbose=False,
    )[0]
    
    for b in results.boxes:
        cls_id = int(b.cls[0])
        conf = float(b.conf[0])
        tid = int(b.id[0]) if b.id is not None else -1
        if cls_id == 5 or conf > 0.8: # bus or high conf
            bbox = [int(v) for v in b.xyxy[0].tolist()]
            x1, y1, x2, y2 = bbox
            veh_crop = letterboxed[max(0, y1):min(letterboxed.shape[0], y2), max(0, x1):min(letterboxed.shape[1], x2)]
            plate_crop = extract_plate_crop(veh_crop)
            
            p_res = read_plate_image(plate_crop, min_confidence=0.15) if plate_crop is not None else []
            v_res = read_plate_image(veh_crop, min_confidence=0.15) if veh_crop is not None else []
            
            print(f"Frame {fidx} | Track {tid} cls={cls_id}:")
            print(f"   plate_crop ({plate_crop.shape if plate_crop is not None else None}): {[r['raw_text'] for r in p_res]}")
            print(f"   veh_crop ({veh_crop.shape}): {[r['raw_text'] for r in v_res]}")
            
            all_reads = p_res or v_res
            if all_reads:
                best = max(all_reads, key=lambda x: x["confidence"])
                norm = normalize_plate_text(best["raw_text"])
                print(f"   -> Best: raw='{best['raw_text']}', norm='{norm}', conf={best['confidence']}")
            else:
                print(f"   -> No OCR text detected!")
