import cv2
from pathlib import Path

cbe_dir = Path("data/footage/CBE")
for vpath in cbe_dir.glob("*.*"):
    cap = cv2.VideoCapture(str(vpath))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Checking {vpath.name} (total {total} frames)...")
    # Check 10 sample frames across the video
    for pos in [10, 100, 500, 1000, 2000, 5000, 10000]:
        if pos >= total:
            continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, f = cap.read()
        if ret:
            # Check if right side has yellow/orange bus
            h, w = f.shape[:2]
            sample_crop = f[int(h*0.3):int(h*0.6), int(w*0.8):w]
            # Save thumbnail
            cv2.imwrite(f"scratch/thumb_{vpath.stem}_{pos}.jpg", cv2.resize(f, (320, 180)))
print("Done sampling thumbnails.")
