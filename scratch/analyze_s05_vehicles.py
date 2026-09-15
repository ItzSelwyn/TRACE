import json
from pathlib import Path
from collections import defaultdict

p = Path("data/ground_truth/cityflow_train_gt.jsonl")
veh_records = defaultdict(list)
with open(p, "r") as f:
    for line in f:
        d = json.loads(line)
        veh_records[d["vehicle_id"]].append(d)

cam_order = {"c020": 1, "c023": 2, "c028": 3, "c029": 4}

cross_cam_vehs = []
for vid, recs in veh_records.items():
    cams = sorted(list(set(r["camera_id"] for r in recs)), key=lambda c: cam_order.get(c, 99))
    if len(cams) >= 2:
        cam_sightings = {}
        for r in sorted(recs, key=lambda r: r["frame_id"]):
            c = r["camera_id"]
            if c not in cam_sightings:
                cam_sightings[c] = r["frame_id"]
        cross_cam_vehs.append({
            "vehicle_id": vid,
            "camera_count": len(cams),
            "cameras": cams,
            "first_frames": cam_sightings,
            "total_detections": len(recs)
        })

cross_cam_vehs.sort(key=lambda x: (x["camera_count"], x["total_detections"]), reverse=True)
print(f"Total cross-camera vehicles: {len(cross_cam_vehs)}")

print("\nTop 4-camera vehicles:")
for v in [x for x in cross_cam_vehs if x["camera_count"] == 4][:12]:
    vid = v["vehicle_id"]
    cams = v["cameras"]
    tot = v["total_detections"]
    ff = v["first_frames"]
    print(f"Vehicle {vid}: cameras={cams}, detections={tot}, frames={ff}")

print("\nTop 3-camera vehicles:")
for v in [x for x in cross_cam_vehs if x["camera_count"] == 3][:6]:
    vid = v["vehicle_id"]
    cams = v["cameras"]
    tot = v["total_detections"]
    ff = v["first_frames"]
    print(f"Vehicle {vid}: cameras={cams}, detections={tot}, frames={ff}")

print("\nTop 2-camera vehicles:")
for v in [x for x in cross_cam_vehs if x["camera_count"] == 2][:6]:
    vid = v["vehicle_id"]
    cams = v["cameras"]
    tot = v["total_detections"]
    ff = v["first_frames"]
    print(f"Vehicle {vid}: cameras={cams}, detections={tot}, frames={ff}")
