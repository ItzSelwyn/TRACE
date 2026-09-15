import json
from pathlib import Path

cameras = {
    "c020": [-90.675620, 42.500280],
    "c023": [-90.681350, 42.499480],
    "c028": [-90.688350, 42.498700],
    "c029": [-90.693500, 42.499480],
}

# High-precision road centerline waypoints extracted from OpenStreetMap
c020_c023 = [
    [-90.675620, 42.500280],
    [-90.676124, 42.499791],
    [-90.676604, 42.499721],
    [-90.677018, 42.499663],
    [-90.677511, 42.499607],
    [-90.678013, 42.499542],
    [-90.678775, 42.499443],
    [-90.679775, 42.499325],
    [-90.680302, 42.499262],
    [-90.680839, 42.499197],
    [-90.681350, 42.499480]
]

c023_c028 = [
    [-90.681350, 42.499480],
    [-90.681893, 42.499078],
    [-90.682806, 42.498956],
    [-90.682982, 42.498933],
    [-90.684021, 42.498801],
    [-90.684353, 42.498759],
    [-90.685229, 42.498657],
    [-90.685408, 42.498635],
    [-90.685924, 42.498571],
    [-90.686716, 42.498473],
    [-90.687319, 42.498405],
    [-90.687677, 42.498364],
    [-90.688028, 42.498439],
    [-90.688350, 42.498700]
]

c028_c029 = [
    [-90.688350, 42.498700],
    [-90.688677, 42.498275],
    [-90.688923, 42.498214],
    [-90.689581, 42.498114],
    [-90.690607, 42.497978],
    [-90.690877, 42.498098],
    [-90.690939, 42.498122],
    [-90.692031, 42.498557],
    [-90.693156, 42.499066],
    [-90.693295, 42.499115],
    [-90.693500, 42.499480]
]

c020_c028 = c020_c023 + c023_c028[1:]
c023_c029 = c023_c028 + c028_c029[1:]
c020_c029 = c020_c023 + c023_c028[1:] + c028_c029[1:]

segments = {
    "c020_c023": c020_c023,
    "c023_c020": list(reversed(c020_c023)),
    "c023_c028": c023_c028,
    "c028_c023": list(reversed(c023_c028)),
    "c028_c029": c028_c029,
    "c029_c028": list(reversed(c028_c029)),
    "c020_c028": c020_c028,
    "c028_c020": list(reversed(c020_c028)),
    "c023_c029": c023_c029,
    "c029_c023": list(reversed(c023_c029)),
    "c020_c029": c020_c029,
    "c029_c020": list(reversed(c020_c029)),
}

# 1. Write backend/road_corridor_geometry.json
json_path = Path("backend/road_corridor_geometry.json")
json_path.write_text(json.dumps(segments, indent=2), encoding="utf-8")
print(f"Wrote {json_path}")

# 2. Write frontend/src/data/roadGeometry.ts
ts_path = Path("frontend/src/data/roadGeometry.ts")
header = '/**\n * Pre-computed high-precision street geometry coordinates for the TRACE camera corridor.\n * Extracted from OpenStreetMap road network for CityFlow S05 (Dubuque, Iowa).\n * Snaps vehicle trajectories precisely to street centerlines, intersections, and curves.\n */\n\n'
cameras_block = f"export const CORRIDOR_CAMERAS: Record<string, [number, number]> = {json.dumps(cameras, indent=2)};\n\n"
segments_block = f"export const ROAD_SEGMENTS: Record<string, [number, number][]> = {json.dumps(segments, indent=2)};\n\n"

functions_block = """export function matchCameraId(lng: number, lat: number, name?: string): string | null {
  if (name) {
    const s = name.toLowerCase();
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
"""

ts_path.write_text(header + cameras_block + segments_block + functions_block, encoding="utf-8")
print(f"Wrote {ts_path}")

# 3. Update PostgreSQL database
try:
    import psycopg2
    import sys
    sys.path.insert(0, "backend")
    from app.config import settings
    db_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(db_url)
    with conn.cursor() as cur:
        s05_cams = [
            ("c1000000-0000-0000-0000-000000000001", "Camera 020 (University Ave & Walnut)", -90.675620, 42.500280, "S05-A"),
            ("c2000000-0000-0000-0000-000000000002", "Camera 023 (University Ave & Nevada)", -90.681350, 42.499480, "S05-A"),
            ("c3000000-0000-0000-0000-000000000003", "Camera 028 (Grandview Roundabout)", -90.688350, 42.498700, "S05-B"),
            ("c4000000-0000-0000-0000-000000000004", "Camera 029 (University Ave & Alta Pl)", -90.693500, 42.499480, "S05-B"),
        ]
        for cid, name, lng, lat, zone in s05_cams:
            cur.execute("""
                UPDATE cameras 
                SET name = %s,
                    zone = %s,
                    status = 'online',
                    location = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                WHERE camera_id = %s;
            """, (name, zone, lng, lat, cid))
        conn.commit()
        print("Updated PostgreSQL database cameras table successfully!")
except Exception as e:
    print("DB update notice:", e)
