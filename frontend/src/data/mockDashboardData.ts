import { DashboardDataPayload } from '../types/dashboard';

/**
 * Default Mock Data matching the TRACE Dashboard UI specification.
 * P2 Backend Engineer can easily replace this file or point components
 * to an API hook (e.g. FastAPI /analytics & /alerts endpoints).
 */
export const mockDashboardData: DashboardDataPayload = {
  topStats: {
    activeScans: 24,
    blacklistsCount: 10,
    systemStatus: 'OPTIMAL',
  },
  cameras: [
    {
      id: 'cam-13',
      cameraCode: 'C13',
      name: 'Camera 13',
      location: 'North Highway 08',
      timestamp: '11-03-2026 Thur 04:31:12 pm (C13)',
      feedImageUrl: '/assets/Dashboard.png', // or highway frame
      status: 'online',
    },
    {
      id: 'cam-14',
      cameraCode: 'C14',
      name: 'Camera 14',
      location: 'East Corridor 04',
      timestamp: '11-03-2026 Thur 04:31:12 pm (C14)',
      feedImageUrl: '/assets/Dashboard.png',
      status: 'online',
    },
    {
      id: 'cam-15',
      cameraCode: 'C15',
      name: 'Camera 15',
      location: 'Central Junction 02',
      timestamp: '11-03-2026 Thur 04:31:12 pm (C15)',
      feedImageUrl: '/assets/Dashboard.png',
      status: 'online',
    },
    {
      id: 'cam-16',
      cameraCode: 'C16',
      name: 'Camera 16',
      location: 'North Highway 08',
      timestamp: '11-03-2026 Thur 04:31:12 pm (C16)',
      feedImageUrl: '/assets/Dashboard.png',
      status: 'online',
    },
  ],
  modelAnalysis: {
    cameraId: 'cam-13',
    cameraName: 'Camera 13',
    location: 'North Highway 08',
    plateNumber: 'TN 01 75 0608',
    ocrConfidence: 94,
    vehicleType: 'SUV',
    color: 'Blue',
    timestamp: '10:23:39 am',
    detectedImageUrl: '/assets/Dashboard.png',
    boundingLabel: 'Vehicle 94%',
  },
  recentAlerts: [
    {
      id: 'alt-101',
      plateNumber: 'TN 37 CY 1234',
      alertType: 'BLACKLIST',
      confidence: 92,
      cameraCode: 'C16',
      cameraName: 'Camera 16',
      location: 'North Highway 08',
      timestamp: '10:22:15 am',
      reviewed: false,
    },
    {
      id: 'alt-102',
      plateNumber: 'TN 22 CY 1608',
      alertType: 'WATCHLIST',
      confidence: 94,
      cameraCode: 'C13',
      cameraName: 'Camera 13',
      location: 'North Highway 08',
      timestamp: '10:19:40 am',
      reviewed: false,
    },
  ],
  networkStats: {
    uptimeFormatted: '5hrs',
    camerasActive: 8,
    camerasDown: 2,
    totalCameras: 10,
  },
};
