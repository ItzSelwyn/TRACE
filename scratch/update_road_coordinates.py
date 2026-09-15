import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Road-snapped camera coordinates (directly on University Ave and Grandview Roundabout centerline)
ROAD_CAMERAS = {
    "c020": {
        "uuid": "c1000000-0000-0000-0000-000000000001",
        "name": "Camera 020 (University Ave & Walnut)",
        "location": "University Ave & Walnut",
        "lng": -90.675620,
        "lat": 42.499860,
    },
    "c023": {
        "uuid": "c2000000-0000-0000-0000-000000000002",
        "name": "Camera 023 (University Ave & Nevada)",
        "location": "University Ave & Nevada",
        "lng": -90.681350,
        "lat": 42.499140,
    },
    "c028": {
        "uuid": "c3000000-0000-0000-0000-000000000003",
        "name": "Camera 028 (Grandview Roundabout)",
        "location": "Grandview Roundabout",
        "lng": -90.688350,
        "lat": 42.498360,
    },
    "c029": {
        "uuid": "c4000000-0000-0000-0000-000000000004",
        "name": "Camera 029 (University Ave & Alta Pl)",
        "location": "University Ave & Alta Pl",
        "lng": -90.693500,
        "lat": 42.499190,
    },
}

# 1. Update data/seed/cameras.json
seed_path = PROJECT_ROOT / "data" / "seed" / "cameras.json"
if seed_path.exists():
    with open(seed_path, "r", encoding="utf-8") as f:
        cams = json.load(f)
    for c in cams:
        for cid, meta in ROAD_CAMERAS.items():
            if c.get("camera_id") == meta["uuid"] or cid in c.get("name", "").lower():
                c["latitude"] = meta["lat"]
                c["longitude"] = meta["lng"]
    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(cams, f, indent=2)
    print("Updated data/seed/cameras.json")

# 2. Update backend/road_corridor_geometry.json
corridor_geom_path = PROJECT_ROOT / "backend" / "road_corridor_geometry.json"
with open(corridor_geom_path, "r", encoding="utf-8") as f:
    orig_geom = json.load(f)

c020 = [ROAD_CAMERAS["c020"]["lng"], ROAD_CAMERAS["c020"]["lat"]]
c023 = [ROAD_CAMERAS["c023"]["lng"], ROAD_CAMERAS["c023"]["lat"]]
c028 = [ROAD_CAMERAS["c028"]["lng"], ROAD_CAMERAS["c028"]["lat"]]
c029 = [ROAD_CAMERAS["c029"]["lng"], ROAD_CAMERAS["c029"]["lat"]]

seg_20_23 = [c020] + orig_geom["c020_c023"][1:-1] + [c023]
seg_23_28 = [c023] + orig_geom["c023_c028"][1:-1] + [c028]
seg_28_29 = [c028] + orig_geom["c028_c029"][1:-1] + [c029]

all_segs = {
    "c020_c023": seg_20_23,
    "c023_c020": list(reversed(seg_20_23)),
    "c023_c028": seg_23_28,
    "c028_c023": list(reversed(seg_23_28)),
    "c028_c029": seg_28_29,
    "c029_c028": list(reversed(seg_28_29)),
    "c020_c028": seg_20_23 + seg_23_28[1:],
    "c028_c020": list(reversed(seg_20_23 + seg_23_28[1:])),
    "c023_c029": seg_23_28 + seg_28_29[1:],
    "c029_c023": list(reversed(seg_23_28 + seg_28_29[1:])),
    "c020_c029": seg_20_23 + seg_23_28[1:] + seg_28_29[1:],
    "c029_c020": list(reversed(seg_20_23 + seg_23_28[1:] + seg_28_29[1:])),
}

with open(corridor_geom_path, "w", encoding="utf-8") as f:
    json.dump(all_segs, f, indent=2)
print("Updated backend/road_corridor_geometry.json")

# 3. Update frontend/src/data/roadGeometry.ts
ts_path = PROJECT_ROOT / "frontend" / "src" / "data" / "roadGeometry.ts"
ts_lines = [
    "/**",
    " * Pre-computed high-precision street geometry coordinates for the TRACE camera corridor.",
    " * Extracted from OpenStreetMap road network for CityFlow S05 (Dubuque, Iowa).",
    " * Snaps vehicle trajectories precisely to street centerlines, intersections, and curves.",
    " */",
    "",
    "export const CORRIDOR_CAMERAS: Record<string, [number, number]> = " + json.dumps({
        "c020": c020,
        "c023": c023,
        "c028": c028,
        "c029": c029,
    }, indent=2) + ";",
    "",
    "export const ROAD_SEGMENTS: Record<string, [number, number][]> = " + json.dumps(all_segs, indent=2) + ";",
    "",
    """export function matchCameraId(lng: number, lat: number, cameraName?: string): string | null {
  if (cameraName) {
    const s = cameraName.toLowerCase();
    if (s.includes('020') || s.includes('c020')) return 'c020';
    if (s.includes('023') || s.includes('c023')) return 'c023';
    if (s.includes('028') || s.includes('c028')) return 'c028';
    if (s.includes('029') || s.includes('c029')) return 'c029';
  }
  let closest: string | null = null;
  let minDist = Infinity;
  for (const [cid, [cLng, cLat]] of Object.entries(CORRIDOR_CAMERAS)) {
    const dist = Math.hypot(lng - cLng, lat - cLat);
    if (dist < 0.008 && dist < minDist) {
      minDist = dist;
      closest = cid;
    }
  }
  return closest;
}

export function getRoadSegment(fromCam: string, toCam: string): [number, number][] {
  const directKey = `${fromCam}_${toCam}`;
  if (ROAD_SEGMENTS[directKey]) {
    return ROAD_SEGMENTS[directKey];
  }

  // Multi-hop path resolution through camera sequence
  const order = ['c020', 'c023', 'c028', 'c029'];
  const iFrom = order.indexOf(fromCam);
  const iTo = order.indexOf(toCam);

  if (iFrom !== -1 && iTo !== -1 && iFrom !== iTo) {
    const result: [number, number][] = [];
    const step = iFrom < iTo ? 1 : -1;
    for (let curr = iFrom; curr !== iTo; curr += step) {
      const nxt = curr + step;
      const segKey = `${order[curr]}_${order[nxt]}`;
      const segCoords = ROAD_SEGMENTS[segKey];
      if (segCoords) {
        if (result.length === 0) {
          result.push(...segCoords);
        } else {
          result.push(...segCoords.slice(1));
        }
      }
    }
    if (result.length > 0) return result;
  }

  // Fallback direct segment
  const fromCoord = CORRIDOR_CAMERAS[fromCam];
  const toCoord = CORRIDOR_CAMERAS[toCam];
  if (fromCoord && toCoord) {
    return [fromCoord, toCoord];
  }
  return [];
}

export function snapTrajectoryToRoads(
  stops: { lng: number; lat: number; cameraName?: string }[]
): [number, number][] {
  if (stops.length < 2) {
    return stops.map((s) => [s.lng, s.lat]);
  }

  const snappedPath: [number, number][] = [];

  for (let i = 0; i < stops.length - 1; i++) {
    const curr = stops[i];
    const next = stops[i + 1];

    const camA = matchCameraId(curr.lng, curr.lat, curr.cameraName);
    const camB = matchCameraId(next.lng, next.lat, next.cameraName);

    if (camA && camB && camA !== camB) {
      const roadWaypoints = getRoadSegment(camA, camB);
      if (roadWaypoints.length > 0) {
        if (snappedPath.length === 0) {
          snappedPath.push(...roadWaypoints);
        } else {
          snappedPath.push(...roadWaypoints.slice(1));
        }
        continue;
      }
    }

    if (snappedPath.length === 0) {
      snappedPath.push([curr.lng, curr.lat]);
    }
    snappedPath.push([next.lng, next.lat]);
  }

  return snappedPath;
}
""",
]

with open(ts_path, "w", encoding="utf-8") as f:
    f.write("\n".join(ts_lines))
print("Updated frontend/src/data/roadGeometry.ts")

# 4. Update PostgreSQL database cameras table
import sys
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from sqlalchemy import text
from app.db.session import get_sync_db

try:
    db = next(get_sync_db())
    for cid, meta in ROAD_CAMERAS.items():
        db.execute(text(
            "UPDATE cameras SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE camera_id = :uuid"
        ), {"lng": meta["lng"], "lat": meta["lat"], "uuid": meta["uuid"]})
    db.commit()
    print("Updated PostgreSQL cameras table with new coordinates")
except Exception as e:
    print(f"Warning updating DB cameras: {e}")
