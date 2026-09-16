import cv2
from pathlib import Path

cbe_dir = Path("data/footage/CBE")
for v in cbe_dir.glob("*.*"):
    cap = cv2.VideoCapture(str(v))
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"{v.name}: {count} frames, {fps:.1f} fps, {w}x{h}")
