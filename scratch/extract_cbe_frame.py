import cv2

cap = cv2.VideoCapture("data/footage/CBE/3.MOV")
cap.set(cv2.CAP_PROP_POS_FRAMES, 1600)
ret, frame = cap.read()
if ret:
    cv2.imwrite("scratch/frame_1600.jpg", frame)
    print("Wrote scratch/frame_1600.jpg, shape:", frame.shape)
else:
    print("Could not read frame 1600")
