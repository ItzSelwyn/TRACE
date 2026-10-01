/**
 * Map Profiles for TRACE GIS Visualizations.
 * Supports CityFlow (S04, S05 in Dubuque, Iowa) and Coimbatore (CBE in Kuniyamuthur, Tamil Nadu).
 */

import { ROAD_SEGMENTS as CITYFLOW_ROAD_SEGMENTS } from './roadGeometry';

export interface CameraLocationConfig {
  id: string;
  name: string;
  location: string;
  lng: number;
  lat: number;
}

export interface MapProfileConfig {
  id: string;
  name: string;
  center: [number, number]; // [lng, lat]
  zoom: number;
  cameras: Record<string, CameraLocationConfig>;
  roadSegments: Record<string, [number, number][]>;
}

// Coimbatore Road Segment Coordinates along Palghat Rd & Kovaipudur Rd matching ground-truth OSM nodes
const CBE_ROAD_SEGMENTS: Record<string, [number, number][]> = {
  c020_c023: [
    [76.951820, 10.939350],
    [76.951690, 10.938788],
    [76.951040, 10.936340],
  ],
  c023_c020: [
    [76.951040, 10.936340],
    [76.951690, 10.938788],
    [76.951820, 10.939350],
  ],
  c023_c028: [
    [76.951040, 10.936340],
    [76.950968, 10.936172],
    [76.950076, 10.933942],
    [76.949870, 10.933350],
  ],
  c028_c023: [
    [76.949870, 10.933350],
    [76.950076, 10.933942],
    [76.950968, 10.936172],
    [76.951040, 10.936340],
  ],
  c023_c029: [
    [76.951040, 10.936340],
    [76.950700, 10.936790],
    [76.949970, 10.936940],
    [76.949350, 10.937140],
    [76.948940, 10.937430],
  ],
  c029_c023: [
    [76.948940, 10.937430],
    [76.949350, 10.937140],
    [76.949970, 10.936940],
    [76.950700, 10.936790],
    [76.951040, 10.936340],
  ],
  c020_c028: [
    [76.951820, 10.939350],
    [76.951690, 10.938788],
    [76.951040, 10.936340],
    [76.950968, 10.936172],
    [76.950076, 10.933942],
    [76.949870, 10.933350],
  ],
  c028_c020: [
    [76.949870, 10.933350],
    [76.950076, 10.933942],
    [76.950968, 10.936172],
    [76.951040, 10.936340],
    [76.951690, 10.938788],
    [76.951820, 10.939350],
  ],
  c020_c029: [
    [76.951820, 10.939350],
    [76.951690, 10.938788],
    [76.951040, 10.936340],
    [76.950700, 10.936790],
    [76.949970, 10.936940],
    [76.949350, 10.937140],
    [76.948940, 10.937430],
  ],
  c029_c020: [
    [76.948940, 10.937430],
    [76.949350, 10.937140],
    [76.949970, 10.936940],
    [76.950700, 10.936790],
    [76.951040, 10.936340],
    [76.951690, 10.938788],
    [76.951820, 10.939350],
  ],
  c028_c029: [
    [76.949870, 10.933350],
    [76.950076, 10.933942],
    [76.950968, 10.936172],
    [76.951040, 10.936340],
    [76.950700, 10.936790],
    [76.949970, 10.936940],
    [76.949350, 10.937140],
    [76.948940, 10.937430],
  ],
  c029_c028: [
    [76.948940, 10.937430],
    [76.949350, 10.937140],
    [76.949970, 10.936940],
    [76.950700, 10.936790],
    [76.951040, 10.936340],
    [76.950968, 10.936172],
    [76.950076, 10.933942],
    [76.949870, 10.933350],
  ],
};

export const MAP_PROFILES: Record<string, MapProfileConfig> = {
  cityflow: {
    id: 'cityflow',
    name: 'CityFlow Corridor (Dubuque, Iowa)',
    center: [-90.6847, 42.4991],
    zoom: 14.8,
    cameras: {
      c020: {
        id: 'c020',
        name: 'Camera 020 (University Ave & Walnut)',
        location: 'University Ave & Walnut',
        lng: -90.675620,
        lat: 42.499860,
      },
      c023: {
        id: 'c023',
        name: 'Camera 023 (University Ave & Nevada)',
        location: 'University Ave & Nevada',
        lng: -90.681350,
        lat: 42.499140,
      },
      c028: {
        id: 'c028',
        name: 'Camera 028 (Grandview Roundabout)',
        location: 'Grandview Roundabout',
        lng: -90.688350,
        lat: 42.498360,
      },
      c029: {
        id: 'c029',
        name: 'Camera 029 (University Ave & Alta Pl)',
        location: 'University Ave & Alta Pl',
        lng: -90.693500,
        lat: 42.499190,
      },
    },
    roadSegments: CITYFLOW_ROAD_SEGMENTS,
  },
  coimbatore: {
    id: 'coimbatore',
    name: 'Coimbatore Corridor (Kuniyamuthur / SKCET)',
    center: [76.950600, 10.936500],
    zoom: 15.0,
    cameras: {
      c020: {
        id: 'c020',
        name: 'Camera 020 (Palghat Rd North)',
        location: 'Palghat Rd North',
        lng: 76.951820,
        lat: 10.939350,
      },
      c023: {
        id: 'c023',
        name: 'Camera 023 (Palghat Rd Junction)',
        location: 'Palghat Rd Junction',
        lng: 76.951040,
        lat: 10.936340,
      },
      c028: {
        id: 'c028',
        name: 'Camera 028 (Palghat Rd South)',
        location: 'Palghat Rd South',
        lng: 76.949870,
        lat: 10.933350,
      },
      c029: {
        id: 'c029',
        name: 'Camera 029 (Kovaipudur Rd)',
        location: 'Kovaipudur Rd',
        lng: 76.948940,
        lat: 10.937430,
      },
    },
    roadSegments: CBE_ROAD_SEGMENTS,
  },
};

export function getMapProfile(profileKey?: string): MapProfileConfig {
  const key = (profileKey || 'cityflow').toLowerCase();
  if (key === 'cbe' || key === 'coimbatore') {
    return MAP_PROFILES.coimbatore;
  }
  return MAP_PROFILES[key] || MAP_PROFILES.cityflow;
}
