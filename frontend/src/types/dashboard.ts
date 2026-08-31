/**
 * TRACE Dashboard Data Interfaces
 * Designed for easy P2 Backend Integration (FastAPI REST / WebSocket endpoints)
 */

export type SystemStatusType = 'OPTIMAL' | 'DEGRADED' | 'CRITICAL';
export type AlertSeverityType = 'BLACKLIST' | 'WATCHLIST' | 'ANOMALY' | 'IMPOSSIBLE_JOURNEY';

export interface TopSummaryStats {
  activeScans: number;
  blacklistsCount: number;
  systemStatus: SystemStatusType;
}

export interface CameraFeedItem {
  id: string;
  cameraCode: string;
  name: string;
  location: string;
  timestamp: string;
  feedImageUrl: string;
  status: 'online' | 'degraded' | 'down';
}

export interface ModelAnalysisData {
  cameraId: string;
  cameraName: string;
  location: string;
  plateNumber: string;
  ocrConfidence: number; // e.g. 94 for 94%
  vehicleType: string;   // e.g. "SUV"
  color: string;         // e.g. "Blue"
  timestamp: string;     // e.g. "10:23:39 am"
  detectedImageUrl: string;
  boundingLabel: string; // e.g. "Vehicle 94%"
  bbox?: { x: number; y: number; width: number; height: number };
}

export interface DashboardAlertItem {
  id: string;
  plateNumber: string;
  alertType: AlertSeverityType;
  confidence: number;
  cameraCode: string;
  cameraName: string;
  location: string;
  timestamp: string;
  reviewed: boolean;
}

export interface NetworkAnalysisStats {
  uptimeFormatted: string; // e.g. "5hrs"
  camerasActive: number;
  camerasDown: number;
  totalCameras: number;
}

export interface DashboardDataPayload {
  topStats: TopSummaryStats;
  cameras: CameraFeedItem[];
  modelAnalysis: ModelAnalysisData;
  recentAlerts: DashboardAlertItem[];
  networkStats: NetworkAnalysisStats;
}
