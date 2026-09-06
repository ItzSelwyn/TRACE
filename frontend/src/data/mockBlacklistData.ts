import { BlacklistEntry } from '../types/blacklist';

export const mockBlacklistEntries: BlacklistEntry[] = [
  // Page 1 entries matching the exact design screenshot
  {
    id: 'bl-01',
    plateNumber: 'TN 37 CY 1234',
    reason: "Tracing vehicle's trajectory",
    dateAdded: '1st September 2026',
    timeAdded: '10:23:43 am',
    lastFound: '2hrs ago',
    cameraName: 'Camera 16',
    location: 'North Highway 16',
    active: true,
  },
  {
    id: 'bl-02',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Illegal transportation',
    dateAdded: '2nd September 2026',
    timeAdded: '11:22:33 pm',
    lastFound: '1hr ago',
    cameraName: 'Camera 12',
    location: 'Central Junction 04',
    active: true,
  },
  {
    id: 'bl-03',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Impossible travel',
    dateAdded: '3rd September 2026',
    timeAdded: '07:12:02 am',
    lastFound: '3hrs ago',
    cameraName: 'Camera 08',
    location: 'East Ring Road 02',
    active: true,
  },
  {
    id: 'bl-04',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Impossible travel',
    dateAdded: '3rd September 2026',
    timeAdded: '07:12:02 am',
    lastFound: '3hrs ago',
    cameraName: 'Camera 19',
    location: 'West Bypass 11',
    active: true,
  },
  {
    id: 'bl-05',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Illegal transportation',
    dateAdded: '2nd September 2026',
    timeAdded: '11:22:33 pm',
    lastFound: '1hr ago',
    cameraName: 'Camera 14',
    location: 'South Boulevard 07',
    active: true,
  },
  {
    id: 'bl-06',
    plateNumber: 'TN 37 CY 1234',
    reason: "Tracing vehicle's trajectory",
    dateAdded: '1st September 2026',
    timeAdded: '10:23:43 am',
    lastFound: '2hrs ago',
    cameraName: 'Camera 16',
    location: 'North Highway 16',
    active: true,
  },
  {
    id: 'bl-07',
    plateNumber: 'TN 37 CY 1234',
    reason: "Tracing vehicle's trajectory",
    dateAdded: '1st September 2026',
    timeAdded: '10:23:43 am',
    lastFound: '2hrs ago',
    cameraName: 'Camera 16',
    location: 'North Highway 16',
    active: true,
  },
  {
    id: 'bl-08',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Illegal transportation',
    dateAdded: '2nd September 2026',
    timeAdded: '11:22:33 pm',
    lastFound: '1hr ago',
    cameraName: 'Camera 05',
    location: 'Harbor Road 03',
    active: true,
  },
  {
    id: 'bl-09',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Impossible travel',
    dateAdded: '3rd September 2026',
    timeAdded: '07:12:02 am',
    lastFound: '3hrs ago',
    cameraName: 'Camera 11',
    location: 'Airport Expressway 01',
    active: true,
  },
  {
    id: 'bl-10',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Illegal transportation',
    dateAdded: '2nd September 2026',
    timeAdded: '11:22:33 pm',
    lastFound: '1hr ago',
    cameraName: 'Camera 15',
    location: 'Industrial Sector 08',
    active: true,
  },
  {
    id: 'bl-11',
    plateNumber: 'TN 37 CY 1234',
    reason: 'Illegal transportation',
    dateAdded: '2nd September 2026',
    timeAdded: '11:22:33 pm',
    lastFound: '1hr ago',
    cameraName: 'Camera 02',
    location: 'Metro Terminal 06',
    active: true,
  },
  // Additional pages to support full 10-page pagination
  {
    id: 'bl-12',
    plateNumber: 'KA 03 HA 9821',
    reason: 'Stolen vehicle reported',
    dateAdded: '31st August 2026',
    timeAdded: '04:15:10 pm',
    lastFound: '4hrs ago',
    cameraName: 'Camera 09',
    location: 'Tech Park Gate 01',
    active: true,
  },
  {
    id: 'bl-13',
    plateNumber: 'MH 12 QX 4550',
    reason: 'Speed limit violation loop',
    dateAdded: '30th August 2026',
    timeAdded: '09:40:12 am',
    lastFound: '6hrs ago',
    cameraName: 'Camera 03',
    location: 'Western Arterial 05',
    active: true,
  },
  // Further records for pages 3-10
  ...Array.from({ length: 97 }, (_, i) => {
    const idx = i + 14;
    const reasons = [
      'Illegal transportation',
      "Tracing vehicle's trajectory",
      'Impossible travel',
      'Duplicate plate anomaly',
      'Stolen vehicle reported',
    ];
    const states = ['TN', 'KA', 'MH', 'DL', 'KL', 'TS', 'GJ', 'WB'];
    const state = states[i % states.length];
    const rgn = String((i % 38) + 1).padStart(2, '0');
    const letters = String.fromCharCode(65 + (i % 26)) + String.fromCharCode(65 + ((i + 3) % 26));
    const num = String(1000 + ((i * 37) % 9000));
    const day = (i % 28) + 1;
    const suffix = day === 1 || day === 21 ? 'st' : day === 2 || day === 22 ? 'nd' : day === 3 || day === 23 ? 'rd' : 'th';
    const hoursAgo = (i % 24) + 4;
    const camNum = String((i % 24) + 1).padStart(2, '0');

    return {
      id: `bl-${idx}`,
      plateNumber: `${state} ${rgn} ${letters} ${num}`,
      reason: reasons[i % reasons.length],
      dateAdded: `${day}${suffix} August 2026`,
      timeAdded: `${String((i % 12) + 1).padStart(2, '0')}:${String((i * 7) % 60).padStart(2, '0')}:${String((i * 13) % 60).padStart(2, '0')} ${i % 2 === 0 ? 'am' : 'pm'}`,
      lastFound: `${hoursAgo}hrs ago`,
      cameraName: `Camera ${camNum}`,
      location: `Sector Highway ${camNum}`,
      active: true,
    };
  }),
];
