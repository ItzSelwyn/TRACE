import { VehicleTraceDataPayload } from '../types/vehicleTrace';

/**
 * Default Mock Data for Vehicle Trace Screen matching CityFlow S05 Corridor.
 * Automatically refreshed via GET /vehicles/{plate}/trajectory when backend is live.
 */
export const mockVehicleTraceData: VehicleTraceDataPayload = {
  searchedPlate: '334',
  totalScans: 4,
  totalAnomalies: 0,
  selectedTimeWindow: '24hrs',
  chronology: [
    {
      id: 'chron-1',
      plateNumber: 'Vehicle 334',
      timestamp: '00:05.5 AM',
      ocrConfidence: 95,
      cameraName: 'Camera 020 (University Ave & Walnut)',
      location: 'CityFlow S05 Corridor',
      trackedTimeAgo: 'Initial Detection (c020)',
      statusType: 'normal',
      latitude: 42.499860,
      longitude: -90.675620,
    },
    {
      id: 'chron-2',
      plateNumber: 'Vehicle 334',
      timestamp: '00:41.6 AM',
      ocrConfidence: 93,
      cameraName: 'Camera 023 (University Ave & Nevada)',
      location: 'CityFlow S05 Corridor',
      trackedTimeAgo: '+36s from previous camera (46.9 km/h)',
      statusType: 'normal',
      latitude: 42.499140,
      longitude: -90.681350,
    },
    {
      id: 'chron-3',
      plateNumber: 'Vehicle 334',
      timestamp: '01:43.7 AM',
      ocrConfidence: 91,
      cameraName: 'Camera 028 (Grandview Roundabout)',
      location: 'CityFlow S05 Corridor',
      trackedTimeAgo: '+62s from previous camera (34.8 km/h)',
      statusType: 'normal',
      latitude: 42.498360,
      longitude: -90.688350,
    },
    {
      id: 'chron-4',
      plateNumber: 'Vehicle 334',
      timestamp: '02:23.5 AM',
      ocrConfidence: 94,
      cameraName: 'Camera 029 (University Ave & Alta Pl)',
      location: 'CityFlow S05 Corridor',
      trackedTimeAgo: '+40s from previous camera (32.6 km/h)',
      statusType: 'normal',
      latitude: 42.499190,
      longitude: -90.693500,
    },
  ],
  mapPoints: [
    { id: 'pt-1', cameraName: 'Camera 020 (University Ave & Walnut)', location: 'CityFlow S05 Corridor', pointType: 'scanned', xPercent: 18, yPercent: 45 },
    { id: 'pt-2', cameraName: 'Camera 023 (University Ave & Nevada)', location: 'CityFlow S05 Corridor', pointType: 'trajectory', xPercent: 38, yPercent: 48 },
    { id: 'pt-3', cameraName: 'Camera 028 (Grandview Roundabout)', location: 'CityFlow S05 Corridor', pointType: 'trajectory', xPercent: 62, yPercent: 55 },
    { id: 'pt-4', cameraName: 'Camera 029 (University Ave & Alta Pl)', location: 'CityFlow S05 Corridor', pointType: 'trajectory', xPercent: 82, yPercent: 46 },
  ],
};
