/**
 * TRACE Vehicle Trace Data Interfaces
 * Designed for P2 Backend Integration (FastAPI /vehicles/{plate}/trajectory)
 */

export type ChronologyStatusType = 'normal' | 'anomaly' | 'blacklisted';

export interface ChronologyObservation {
  id: string;
  plateNumber: string;
  timestamp: string;      // e.g. "07:08:35 am"
  ocrConfidence: number;  // e.g. 92 for 92%
  cameraName: string;     // e.g. "Camera 16"
  location: string;       // e.g. "North Highway 08"
  trackedTimeAgo: string; // e.g. "Tracked 2 mins ago"
  statusType: ChronologyStatusType;
  statusMessage?: string; // e.g. "Anomaly detected / Tracked 30mins ago"
}

export interface TrajectoryMapPoint {
  id: string;
  cameraName: string;
  location: string;
  pointType: 'scanned' | 'trajectory' | 'anomaly';
  xPercent: number; // For SVG map placement percentage (0-100)
  yPercent: number;
}

export interface VehicleTraceDataPayload {
  searchedPlate: string;
  totalScans: number;
  totalAnomalies: number;
  selectedTimeWindow: string; // e.g. "24hrs"
  chronology: ChronologyObservation[];
  mapPoints: TrajectoryMapPoint[];
}
