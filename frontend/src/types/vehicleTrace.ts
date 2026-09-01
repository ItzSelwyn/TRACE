/**
 * TRACE Vehicle Trace Data Interfaces
 * Designed for P2 Backend Integration (FastAPI /vehicles/{plate}/trajectory)
 *
 * M3 update: added identity evidence breakdown and confidence label fields
 */

export type ChronologyStatusType = 'normal' | 'anomaly' | 'blacklisted';

/** Match confidence from the M3 identity scoring engine */
export type MatchConfidenceLabel = 'confirmed' | 'candidate' | 'no_match' | 'low_confidence';

/** Evidence breakdown for NFR-07 explainability (from backend EvidenceBreakdown schema) */
export interface IdentityEvidence {
  plate_similarity: number;          // 0–1
  ocr_confidence_component: number;  // 0–1, reliability-weighted
  attribute_match: number;           // 0–1
  camera_reliability_weight: number; // 0–1
}

export interface ChronologyObservation {
  id: string;
  plateNumber: string;
  timestamp: string;      // e.g. "07:08:35 am"
  ocrConfidence: number;  // e.g. 92 for 92%
  cameraName: string;     // e.g. "Camera 16"
  location: string;       // e.g. "North Highway 08"
  trackedTimeAgo: string; // e.g. "Tracked 2 mins ago"
  statusType: ChronologyStatusType;
  statusMessage?: string; // e.g. "Low Confidence Match" or "Anomaly detected"

  // M3 identity fields
  identityScore?: number;                  // 0–1 from backend identity_score
  confidenceLabel?: MatchConfidenceLabel;  // from backend match_confidence_label
  evidence?: IdentityEvidence;             // full evidence breakdown
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
