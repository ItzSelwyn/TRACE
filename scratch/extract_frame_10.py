import cv2

cap = cv2.VideoCapture("data/footage/CBE/3.MOV")
cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
ret, frame = cap.read()
if ret:
    cv2.imwrite("scratch/bus_frame_10.jpg", frame)
    print("Extracted bus_frame_10.jpg:", frame.shape)
