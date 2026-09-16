import cv2

frame = cv2.imread("scratch/frame_1600.jpg")
h, w = frame.shape[:2]
print(f"Full frame shape: {w}x{h}")

bus_full = frame[0:800, 1500:1920]
cv2.imwrite("scratch/bus_full.jpg", bus_full)

bumper = frame[350:650, 1550:1920]
cv2.imwrite("scratch/bus_bumper.jpg", bumper)
