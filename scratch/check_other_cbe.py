import cv2
from pathlib import Path

for name in ["1.mp4", "2.mp4", "4.mp4"]:
    vpath = Path("data/footage/CBE") / name
    if not vpath.exists():
        continue
    cap = cv2.VideoCapture(str(vpath))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"{name}: total {total} frames")
    for pos in [0, 50, 100, 200, 500, 1000, 2000, 3000]:
        if pos >= total:
            continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = cap.read()
        if ret:
            # Check the right side
            h, w = frame.shape[:2]
            right_crop = frame[0:h, int(w*0.7):w]
            cv2.imwrite(f"scratch/{name}_{pos}.jpg", cv2.resize(right_crop, (320, 320)))
print("Done saving crops.")
