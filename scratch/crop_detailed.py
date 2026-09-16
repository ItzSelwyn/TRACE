import cv2

frame = cv2.imread("scratch/frame_1600.jpg")
h, w = frame.shape[:2]
# Crop the entire front right of the bus in original resolution
crop = frame[400:750, 1600:1920]
cv2.imwrite("scratch/bumper_detailed.jpg", crop)
print("Saved scratch/bumper_detailed.jpg, shape:", crop.shape)
