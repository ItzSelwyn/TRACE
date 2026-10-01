import { VehicleTraceDataPayload } from '../types/vehicleTrace';

/**
 * Default Mock Data for Vehicle Trace Screen matching CityFlow S05 / S04 Corridor (Dubuque, Iowa).
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
      location: 'CityFlow Corridor',
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
      location: 'CityFlow Corridor',
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
      location: 'CityFlow Corridor',
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
      location: 'CityFlow Corridor',
      trackedTimeAgo: '+40s from previous camera (32.6 km/h)',
      statusType: 'normal',
      latitude: 42.499190,
      longitude: -90.693500,
    },
  ],
  mapPoints: [
    { id: 'pt-1', cameraName: 'Camera 020 (University Ave & Walnut)', location: 'CityFlow Corridor', pointType: 'scanned', xPercent: 18, yPercent: 45 },
    { id: 'pt-2', cameraName: 'Camera 023 (University Ave & Nevada)', location: 'CityFlow Corridor', pointType: 'trajectory', xPercent: 38, yPercent: 48 },
    { id: 'pt-3', cameraName: 'Camera 028 (Grandview Roundabout)', location: 'CityFlow Corridor', pointType: 'trajectory', xPercent: 62, yPercent: 55 },
    { id: 'pt-4', cameraName: 'Camera 029 (University Ave & Alta Pl)', location: 'CityFlow Corridor', pointType: 'trajectory', xPercent: 82, yPercent: 46 },
  ],
};

/**
 * Default Mock Data for Vehicle Trace Screen matching Coimbatore CBE Corridor (Palghat Rd & Kovaipudur Rd near SKCET).
 */
export const mockCbeVehicleTraceDataTN47: VehicleTraceDataPayload = {
  searchedPlate: 'TN47A1507',
  totalScans: 3,
  totalAnomalies: 0,
  selectedTimeWindow: '24hrs',
  chronology: [
    {
      id: 'cbe-chron-1',
      plateNumber: 'TN47A1507',
      timestamp: '05:30.1 AM',
      ocrConfidence: 94,
      cameraName: 'Camera 020 (Palghat Rd North)',
      location: 'Palghat Road, Kuniyamuthur',
      trackedTimeAgo: 'Initial Detection (c020)',
      statusType: 'normal',
      latitude: 10.939350,
      longitude: 76.951820,
    },
    {
      id: 'cbe-chron-2',
      plateNumber: 'TN47A1507',
      timestamp: '05:30.8 AM',
      ocrConfidence: 91,
      cameraName: 'Camera 023 (Palghat Rd Junction)',
      location: 'Palghat Road, Kuniyamuthur',
      trackedTimeAgo: '+44s from previous camera (42.1 km/h)',
      statusType: 'normal',
      latitude: 10.936340,
      longitude: 76.951040,
    },
    {
      id: 'cbe-chron-3',
      plateNumber: 'TN47A1507',
      timestamp: '05:31.6 AM',
      ocrConfidence: 89,
      cameraName: 'Camera 028 (Palghat Rd South)',
      location: 'Palghat Road, Kuniyamuthur',
      trackedTimeAgo: '+50s from previous camera (38.5 km/h)',
      statusType: 'normal',
      latitude: 10.933350,
      longitude: 76.949870,
    },
  ],
  mapPoints: [
    { id: 'cbe-pt-1', cameraName: 'Camera 020 (Palghat Rd North)', location: 'Palghat Road, Kuniyamuthur', pointType: 'scanned', xPercent: 25, yPercent: 30 },
    { id: 'cbe-pt-2', cameraName: 'Camera 023 (Palghat Rd Junction)', location: 'Palghat Road, Kuniyamuthur', pointType: 'trajectory', xPercent: 50, yPercent: 50 },
    { id: 'cbe-pt-3', cameraName: 'Camera 028 (Palghat Rd South)', location: 'Palghat Road, Kuniyamuthur', pointType: 'trajectory', xPercent: 75, yPercent: 70 },
  ],
};

export const mockCbeVehicleTraceDataTN38: VehicleTraceDataPayload = {
  searchedPlate: 'TN38BE5544',
  totalScans: 3,
  totalAnomalies: 0,
  selectedTimeWindow: '24hrs',
  chronology: [
    {
      id: 'cbe-chron-38-1',
      plateNumber: 'TN38BE5544',
      timestamp: '05:40.0 AM',
      ocrConfidence: 93,
      cameraName: 'Camera 029 (Kovaipudur Rd)',
      location: 'Kovaipudur Road',
      trackedTimeAgo: 'Initial Detection (c029)',
      statusType: 'normal',
      latitude: 10.937430,
      longitude: 76.948940,
    },
    {
      id: 'cbe-chron-38-2',
      plateNumber: 'TN38BE5544',
      timestamp: '05:40.8 AM',
      ocrConfidence: 90,
      cameraName: 'Camera 023 (Palghat Rd Junction)',
      location: 'Palghat Road, Kuniyamuthur',
      trackedTimeAgo: '+48s from previous camera (36.4 km/h)',
      statusType: 'normal',
      latitude: 10.936340,
      longitude: 76.951040,
    },
    {
      id: 'cbe-chron-38-3',
      plateNumber: 'TN38BE5544',
      timestamp: '05:41.5 AM',
      ocrConfidence: 92,
      cameraName: 'Camera 020 (Palghat Rd North)',
      location: 'Palghat Road, Kuniyamuthur',
      trackedTimeAgo: '+42s from previous camera (44.0 km/h)',
      statusType: 'normal',
      latitude: 10.939350,
      longitude: 76.951820,
    },
  ],
  mapPoints: [
    { id: 'cbe-pt-38-1', cameraName: 'Camera 029 (Kovaipudur Rd)', location: 'Kovaipudur Road', pointType: 'scanned', xPercent: 20, yPercent: 40 },
    { id: 'cbe-pt-38-2', cameraName: 'Camera 023 (Palghat Rd Junction)', location: 'Palghat Road, Kuniyamuthur', pointType: 'trajectory', xPercent: 50, yPercent: 50 },
    { id: 'cbe-pt-38-3', cameraName: 'Camera 020 (Palghat Rd North)', location: 'Palghat Road, Kuniyamuthur', pointType: 'trajectory', xPercent: 75, yPercent: 30 },
  ],
};

export const mockCbeVehicleTraceData = mockCbeVehicleTraceDataTN47;

export const getMockVehicleTraceData = (activeDataset?: string, plateQuery?: string): VehicleTraceDataPayload => {
  if (activeDataset?.toUpperCase() === 'CBE') {
    if (plateQuery === 'TN38BE5544' || plateQuery?.includes('38') || plateQuery?.includes('5544')) {
      return mockCbeVehicleTraceDataTN38;
    }
    return mockCbeVehicleTraceDataTN47;
  }
  return mockVehicleTraceData;
};
