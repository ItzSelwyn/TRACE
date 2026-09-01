import { DashboardDataPayload } from '../types/dashboard';

/**
 * Default Initial / Fallback Data matching the TRACE Dashboard UI.
 */
export const mockDashboardData: DashboardDataPayload = {
  topStats: {
    activeScans: 37,
    blacklistsCount: 10,
    systemStatus: 'OPTIMAL',
  },
  cameras: [
    {
      id: 'c020',
      cameraCode: 'C020',
      name: 'Camera 020',
      location: 'Live Video Feed',
      timestamp: 'Live',
      feedImageUrl: '/assets/Dashboard.png',
      status: 'online',
    },
    {
      id: 'c023',
      cameraCode: 'C023',
      name: 'Camera 023',
      location: 'Live Video Feed',
      timestamp: 'Live',
      feedImageUrl: '/assets/Dashboard.png',
      status: 'online',
    },
    {
      id: 'c029',
      cameraCode: 'C029',
      name: 'Camera 029',
      location: 'Live Video Feed',
      timestamp: 'Live',
      feedImageUrl: '/assets/Dashboard.png',
      status: 'online',
    },
    {
      id: 'c035',
      cameraCode: 'C035',
      name: 'Camera 035',
      location: 'Live Video Feed',
      timestamp: 'Live',
      feedImageUrl: '/assets/Dashboard.png',
      status: 'online',
    },
  ],
  modelAnalysis: {
    cameraId: 'c020',
    cameraName: 'Camera 020',
    location: 'Live Video Feed',
    plateNumber: 'TRACE-c020-1',
    ocrConfidence: 88,
    vehicleType: 'CAR',
    color: 'WHITE',
    timestamp: 'Live',
    detectedImageUrl: '/assets/Dashboard.png',
    boundingLabel: 'Vehicle (YOLOv8)',
  },
  recentAlerts: [
    {
      id: 'alt-101',
      plateNumber: 'TN 37 CY 1234',
      alertType: 'BLACKLIST',
      confidence: 92,
      cameraCode: 'C020',
      cameraName: 'Camera 020',
      location: 'Live Video Feed',
      timestamp: '10:22:15 am',
      reviewed: false,
    },
    {
      id: 'alt-102',
      plateNumber: 'TN 22 CY 1608',
      alertType: 'WATCHLIST',
      confidence: 94,
      cameraCode: 'C023',
      cameraName: 'Camera 023',
      location: 'Live Video Feed',
      timestamp: '10:19:40 am',
      reviewed: false,
    },
  ],
  networkStats: {
    uptimeFormatted: '5hrs',
    camerasActive: 4,
    camerasDown: 0,
    totalCameras: 4,
  },
};
