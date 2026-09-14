/**
 * Pre-computed high-precision street geometry coordinates for the TRACE camera corridor.
 * Extracted from OpenStreetMap road network for CityFlow S04 (Dubuque, Iowa).
 * Snaps vehicle trajectories precisely to street centerlines, intersections, and curves.
 */

export const CORRIDOR_CAMERAS: Record<string, [number, number]> = {
  c020: [-90.6865, 42.5039],
  c023: [-90.6784, 42.5055],
  c029: [-90.6710, 42.5085],
  c035: [-90.6635, 42.5115],
};

export const ROAD_SEGMENTS: Record<string, [number, number][]> = {
  "c020_c023": [
    [
      -90.686621,
      42.503869
    ],
    [
      -90.686288,
      42.503155
    ],
    [
      -90.686249,
      42.503071
    ],
    [
      -90.68572,
      42.503214
    ],
    [
      -90.685649,
      42.503081
    ],
    [
      -90.684914,
      42.50329
    ],
    [
      -90.684928,
      42.503316
    ],
    [
      -90.684282,
      42.503599
    ],
    [
      -90.683352,
      42.503996
    ],
    [
      -90.682643,
      42.504298
    ],
    [
      -90.682911,
      42.504647
    ],
    [
      -90.683639,
      42.505594
    ],
    [
      -90.684621,
      42.506822
    ],
    [
      -90.68289,
      42.507384
    ],
    [
      -90.681951,
      42.507712
    ],
    [
      -90.680741,
      42.508125
    ],
    [
      -90.680586,
      42.507837
    ],
    [
      -90.680123,
      42.507014
    ],
    [
      -90.679878,
      42.506579
    ],
    [
      -90.679651,
      42.506166
    ],
    [
      -90.679622,
      42.506113
    ],
    [
      -90.679423,
      42.505757
    ],
    [
      -90.679254,
      42.505807
    ],
    [
      -90.679234,
      42.505671
    ],
    [
      -90.679102,
      42.505463
    ],
    [
      -90.679002,
      42.505278
    ],
    [
      -90.678377,
      42.505455
    ]
  ],
  "c023_c029": [
    [
      -90.678377,
      42.505455
    ],
    [
      -90.677903,
      42.505589
    ],
    [
      -90.678194,
      42.506122
    ],
    [
      -90.678049,
      42.506165
    ],
    [
      -90.677779,
      42.506244
    ],
    [
      -90.676764,
      42.506541
    ],
    [
      -90.676471,
      42.506627
    ],
    [
      -90.675355,
      42.506951
    ],
    [
      -90.673064,
      42.507624
    ],
    [
      -90.672944,
      42.507659
    ],
    [
      -90.671672,
      42.508038
    ],
    [
      -90.67113,
      42.508186
    ],
    [
      -90.671272,
      42.508404
    ]
  ],
  "c029_c035": [
    [
      -90.671272,
      42.508404
    ],
    [
      -90.67113,
      42.508186
    ],
    [
      -90.671039,
      42.508212
    ],
    [
      -90.670627,
      42.508329
    ],
    [
      -90.670124,
      42.508473
    ],
    [
      -90.670039,
      42.508497
    ],
    [
      -90.669543,
      42.508649
    ],
    [
      -90.669449,
      42.508678
    ],
    [
      -90.669068,
      42.508794
    ],
    [
      -90.668559,
      42.508936
    ],
    [
      -90.668082,
      42.509084
    ],
    [
      -90.667584,
      42.509238
    ],
    [
      -90.667099,
      42.509383
    ],
    [
      -90.666619,
      42.509523
    ],
    [
      -90.666142,
      42.509669
    ],
    [
      -90.665649,
      42.509818
    ],
    [
      -90.66525,
      42.509942
    ],
    [
      -90.665159,
      42.50997
    ],
    [
      -90.665197,
      42.510039
    ],
    [
      -90.665336,
      42.510296
    ],
    [
      -90.665426,
      42.510462
    ],
    [
      -90.665564,
      42.510717
    ],
    [
      -90.6656,
      42.510783
    ],
    [
      -90.665503,
      42.510812
    ],
    [
      -90.665404,
      42.510841
    ],
    [
      -90.665101,
      42.510932
    ],
    [
      -90.664627,
      42.511073
    ],
    [
      -90.664666,
      42.511143
    ]
  ],
  "c035_c029": [
    [
      -90.664666,
      42.511143
    ],
    [
      -90.664627,
      42.511073
    ],
    [
      -90.665101,
      42.510932
    ],
    [
      -90.665404,
      42.510841
    ],
    [
      -90.665503,
      42.510812
    ],
    [
      -90.6656,
      42.510783
    ],
    [
      -90.665564,
      42.510717
    ],
    [
      -90.665426,
      42.510462
    ],
    [
      -90.665336,
      42.510296
    ],
    [
      -90.665197,
      42.510039
    ],
    [
      -90.665159,
      42.50997
    ],
    [
      -90.66525,
      42.509942
    ],
    [
      -90.665649,
      42.509818
    ],
    [
      -90.666142,
      42.509669
    ],
    [
      -90.666619,
      42.509523
    ],
    [
      -90.667099,
      42.509383
    ],
    [
      -90.667584,
      42.509238
    ],
    [
      -90.668082,
      42.509084
    ],
    [
      -90.668559,
      42.508936
    ],
    [
      -90.669068,
      42.508794
    ],
    [
      -90.669449,
      42.508678
    ],
    [
      -90.669543,
      42.508649
    ],
    [
      -90.670039,
      42.508497
    ],
    [
      -90.670124,
      42.508473
    ],
    [
      -90.670627,
      42.508329
    ],
    [
      -90.671039,
      42.508212
    ],
    [
      -90.67113,
      42.508186
    ],
    [
      -90.671272,
      42.508404
    ]
  ],
  "c029_c023": [
    [
      -90.671272,
      42.508404
    ],
    [
      -90.67113,
      42.508186
    ],
    [
      -90.671672,
      42.508038
    ],
    [
      -90.672944,
      42.507659
    ],
    [
      -90.673064,
      42.507624
    ],
    [
      -90.675355,
      42.506951
    ],
    [
      -90.676471,
      42.506627
    ],
    [
      -90.676764,
      42.506541
    ],
    [
      -90.677779,
      42.506244
    ],
    [
      -90.678049,
      42.506165
    ],
    [
      -90.678194,
      42.506122
    ],
    [
      -90.677903,
      42.505589
    ],
    [
      -90.678377,
      42.505455
    ]
  ],
  "c023_c020": [
    [
      -90.678377,
      42.505455
    ],
    [
      -90.679002,
      42.505278
    ],
    [
      -90.679102,
      42.505463
    ],
    [
      -90.679234,
      42.505671
    ],
    [
      -90.679254,
      42.505807
    ],
    [
      -90.679423,
      42.505757
    ],
    [
      -90.679622,
      42.506113
    ],
    [
      -90.679651,
      42.506166
    ],
    [
      -90.679878,
      42.506579
    ],
    [
      -90.680123,
      42.507014
    ],
    [
      -90.680586,
      42.507837
    ],
    [
      -90.680741,
      42.508125
    ],
    [
      -90.681951,
      42.507712
    ],
    [
      -90.68289,
      42.507384
    ],
    [
      -90.684621,
      42.506822
    ],
    [
      -90.683639,
      42.505594
    ],
    [
      -90.682911,
      42.504647
    ],
    [
      -90.682643,
      42.504298
    ],
    [
      -90.683352,
      42.503996
    ],
    [
      -90.684282,
      42.503599
    ],
    [
      -90.684928,
      42.503316
    ],
    [
      -90.684914,
      42.50329
    ],
    [
      -90.685649,
      42.503081
    ],
    [
      -90.68572,
      42.503214
    ],
    [
      -90.686249,
      42.503071
    ],
    [
      -90.686288,
      42.503155
    ],
    [
      -90.686621,
      42.503869
    ]
  ]
};

export function matchCameraId(lng: number, lat: number, name?: string): string | null {
  if (name) {
    const s = name.toLowerCase();
    if (s.includes('020') || s.includes('c020')) return 'c020';
    if (s.includes('023') || s.includes('c023')) return 'c023';
    if (s.includes('029') || s.includes('c029')) return 'c029';
    if (s.includes('035') || s.includes('c035')) return 'c035';
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
  const order = ['c020', 'c023', 'c029', 'c035'];
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
          // Avoid duplicate junction point
          snappedPath.push(...roadWaypoints.slice(1));
        }
        continue;
      }
    }

    // Default connection if between unknown or custom points
    if (snappedPath.length === 0) {
      snappedPath.push([curr.lng, curr.lat]);
    }
    snappedPath.push([next.lng, next.lat]);
  }

  return snappedPath;
}
