import { VehicleTraceDataPayload } from '../types/vehicleTrace';

/**
 * Default Mock Data for Vehicle Trace Screen matching Image 1 specification.
 * P2 Backend Engineer can easily replace this payload with API data from
 * GET /vehicles/{plate}/trajectory
 */
export const mockVehicleTraceData: VehicleTraceDataPayload = {
  searchedPlate: 'TN 37 CY 1234',
  totalScans: 5,
  totalAnomalies: 2,
  selectedTimeWindow: '24hrs',
  chronology: [
    {
      id: 'chron-1',
      plateNumber: 'TN 37 CY 1234',
      timestamp: '07:08:35 am',
      ocrConfidence: 92,
      cameraName: 'Camera 16',
      location: 'North Highway 08',
      trackedTimeAgo: 'Tracked 2 mins ago',
      statusType: 'normal',
    },
    {
      id: 'chron-2',
      plateNumber: 'TN 22 CY 1608',
      timestamp: '08:10:25 am',
      ocrConfidence: 94,
      cameraName: 'Camera 14',
      location: 'North Highway 04',
      trackedTimeAgo: 'Anomaly detected / Tracked 30mins ago',
      statusType: 'anomaly',
    },
    {
      id: 'chron-3',
      plateNumber: 'TN 11 CY 8061',
      timestamp: '01:23:56 pm',
      ocrConfidence: 91,
      cameraName: 'Camera 13',
      location: 'North Highway 02',
      trackedTimeAgo: 'Tracked 3hrs ago',
      statusType: 'normal',
    },
    {
      id: 'chron-4',
      plateNumber: 'TN 22 CY 1608',
      timestamp: '08:10:25 am',
      ocrConfidence: 80,
      cameraName: 'Camera 15',
      location: 'North Highway 12',
      trackedTimeAgo: 'Blacklisted vehicle / Tracked 20 mins ago',
      statusType: 'blacklisted',
    },
    {
      id: 'chron-5',
      plateNumber: 'TN 11 CY 8061',
      timestamp: '01:23:56 pm',
      ocrConfidence: 91,
      cameraName: 'Camera 13',
      location: 'North Highway 02',
      trackedTimeAgo: 'Tracked 3hrs ago',
      statusType: 'normal',
    },
  ],
  mapPoints: [
    { id: 'pt-1', cameraName: 'Camera 16', location: 'North Highway 08', pointType: 'anomaly', xPercent: 12, yPercent: 48 },
    { id: 'pt-2', cameraName: 'Camera 14', location: 'North Highway 04', pointType: 'trajectory', xPercent: 32, yPercent: 62 },
    { id: 'pt-3', cameraName: 'Camera 13', location: 'North Highway 02', pointType: 'trajectory', xPercent: 55, yPercent: 78 },
    { id: 'pt-4', cameraName: 'Camera 15', location: 'North Highway 12', pointType: 'scanned', xPercent: 72, yPercent: 88 },
    { id: 'pt-5', cameraName: 'Camera 12', location: 'South Exit 01', pointType: 'anomaly', xPercent: 92, yPercent: 88 },
  ],
};
