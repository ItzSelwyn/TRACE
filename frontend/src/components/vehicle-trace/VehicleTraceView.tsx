import React, { useState } from 'react';
import { useDataset } from '../../context/DatasetContext';
import { VehicleTraceDataPayload } from '../../types/vehicleTrace';
import {
  Map,
  MapMarker,
  MarkerContent,
  MarkerTooltip,
  MapRoute,
} from "@/components/ui/map";
import { snapTrajectoryToRoads, matchCameraId } from '../../data/roadGeometry';

export interface CrossCameraPathItem {
  vehicle_id: string;
  label: string;
  description: string;
  camera_count: number;
  cameras: string[];
  is_corridor: boolean;
}

const DEFAULT_CITYFLOW_PATHS: CrossCameraPathItem[] = [
  { vehicle_id: '334', label: 'Vehicle 334 (4-Cam Corridor)', description: 'c020 → c023 → c028 → c029', camera_count: 4, cameras: ['c020', 'c023', 'c028', 'c029'], is_corridor: true },
  { vehicle_id: '396', label: 'Vehicle 396 (4-Cam Corridor)', description: 'c020 → c023 → c028 → c029', camera_count: 4, cameras: ['c020', 'c023', 'c028', 'c029'], is_corridor: true },
  { vehicle_id: '336', label: 'Vehicle 336 (4-Cam Corridor)', description: 'c020 → c023 → c028 → c029', camera_count: 4, cameras: ['c020', 'c023', 'c028', 'c029'], is_corridor: true },
  { vehicle_id: '354', label: 'Vehicle 354 (4-Cam Corridor)', description: 'c020 → c023 → c028 → c029', camera_count: 4, cameras: ['c020', 'c023', 'c028', 'c029'], is_corridor: true },
  { vehicle_id: '420', label: 'Vehicle 420 (c020 → c023 → c028)', description: 'c020 → c023 → c028', camera_count: 3, cameras: ['c020', 'c023', 'c028'], is_corridor: false },
  { vehicle_id: '486', label: 'Vehicle 486 (c028 → c029)', description: 'c028 → c029', camera_count: 2, cameras: ['c028', 'c029'], is_corridor: false },
];

const DEFAULT_CBE_PATHS: CrossCameraPathItem[] = [
  { vehicle_id: 'TN47A1507', label: 'Bus TN47A1507 (Palghat Rd Corridor)', description: 'c020 → c023 → c028', camera_count: 3, cameras: ['c020', 'c023', 'c028'], is_corridor: true },
  { vehicle_id: 'TN38BE5544', label: 'Vehicle TN38BE5544 (Kovaipudur Cutoff)', description: 'c029 → c023 → c020', camera_count: 3, cameras: ['c029', 'c023', 'c020'], is_corridor: true },
  { vehicle_id: 'TN37CY1234', label: 'Vehicle TN37CY1234 (4-Cam Corridor)', description: 'c020 → c023 → c028 → c029', camera_count: 4, cameras: ['c020', 'c023', 'c028', 'c029'], is_corridor: true },
  { vehicle_id: 'KL09AP2311', label: 'Vehicle KL09AP2311 (c020 → c023)', description: 'c020 → c023', camera_count: 2, cameras: ['c020', 'c023'], is_corridor: false },
];

interface VehicleTraceViewProps {
  data: VehicleTraceDataPayload;
  onSearchPlate?: (plateQuery: string) => void;
}

export const VehicleTraceView: React.FC<VehicleTraceViewProps> = ({ 
  data, 
  onSearchPlate 
}) => {
  const { activeDataset, mapProfile } = useDataset();
  const isCbe = mapProfile.id === 'coimbatore' || activeDataset === 'CBE';
  const defaultPaths = isCbe ? DEFAULT_CBE_PATHS : DEFAULT_CITYFLOW_PATHS;

  const [searchQuery, setSearchQuery] = useState(data.searchedPlate || (isCbe ? 'TN47A1507' : '334'));
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedTimestamps, setSelectedTimestamps] = useState<string[]>(['24 hrs ago']);
  const [crossCameraPaths, setCrossCameraPaths] = useState<CrossCameraPathItem[]>(defaultPaths);

  // Sync cross-camera paths when active dataset changes
  React.useEffect(() => {
    setCrossCameraPaths(isCbe ? DEFAULT_CBE_PATHS : DEFAULT_CITYFLOW_PATHS);
    setSearchQuery(data.searchedPlate || (isCbe ? 'TN47A1507' : '334'));
  }, [activeDataset, isCbe]);

  // Keep search input synced if searchedPlate updates from parent
  React.useEffect(() => {
    if (data.searchedPlate) {
      setSearchQuery(data.searchedPlate);
    }
  }, [data.searchedPlate]);

  // Fetch active cross-camera paths dynamically from backend
  React.useEffect(() => {
    let isMounted = true;
    const fetchPaths = async () => {
      try {
        const res = await fetch('/vehicles/cross-camera-paths');
        if (res.ok) {
          const payload = await res.json();
          if (isMounted && payload?.paths && Array.isArray(payload.paths) && payload.paths.length > 0) {
            setCrossCameraPaths(payload.paths);
          }
        }
      } catch (_) {}
    };
    fetchPaths();
    return () => {
      isMounted = false;
    };
  }, [activeDataset]);
  const [selectedLocations, setSelectedLocations] = useState<string[]>([
    'North Highway 16',
    'North Highway 15',
    'North Highway 14',
    'North Highway 13',
  ]);

  const toggleFilter = (list: string[], setList: React.Dispatch<React.SetStateAction<string[]>>, item: string) => {
    if (list.includes(item)) {
      setList(list.filter((i) => i !== item));
    } else {
      setList([...list, item]);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearchPlate) {
      onSearchPlate(searchQuery.trim());
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    if (onSearchPlate) {
      onSearchPlate('');
    }
  };

  // Helper to parse observation timestamps for chronological ordering
  const parseObsTime = (t?: string): number => {
    if (!t) return 0;
    const parsed = Date.parse(t);
    if (!isNaN(parsed)) return parsed;
    const match = t.match(/(\d+):(\d+)(?::(\d+))?(?:\.(\d+))?\s*(am|pm)?/i);
    if (match) {
      let hours = parseInt(match[1], 10);
      const mins = parseInt(match[2], 10);
      const secs = match[3] ? parseInt(match[3], 10) : (match[4] ? parseInt(match[4], 10) : 0);
      const isPm = match[5] && match[5].toLowerCase() === 'pm';
      const isAm = match[5] && match[5].toLowerCase() === 'am';
      if (isPm && hours < 12) hours += 12;
      if (isAm && hours === 12) hours = 0;
      return hours * 3600 + mins * 60 + secs;
    }
    return 0;
  };

  const resolveCameraId = (camName?: string, lng?: number, lat?: number): string => {
    if (camName) {
      const s = camName.toLowerCase();
      if (s.includes('020') || s.includes('c020') || s.includes('20')) return 'c020';
      if (s.includes('023') || s.includes('c023') || s.includes('23')) return 'c023';
      if (s.includes('028') || s.includes('c028') || s.includes('28')) return 'c028';
      if (s.includes('029') || s.includes('c029') || s.includes('29')) return 'c029';
    }
    if (typeof lng === 'number' && typeof lat === 'number') {
      const matched = matchCameraId(lng, lat, camName);
      if (matched) return matched;
    }
    return 'c020';
  };

  const hasVehicleSelected = Boolean(searchQuery.trim() || data.searchedPlate?.trim()) && data.chronology.length > 0;

  // Sort observations strictly by observation timestamp order
  const sortedChronology = [...data.chronology].sort((a, b) => {
    const tA = parseObsTime(a.timestamp);
    const tB = parseObsTime(b.timestamp);
    return tA - tB;
  });

  const startingCameraId = hasVehicleSelected && sortedChronology.length > 0
    ? resolveCameraId(sortedChronology[0].cameraName, sortedChronology[0].longitude, sortedChronology[0].latitude)
    : null;

  // Extract route coordinates and stops dynamically from chronological observations
  const validStops = hasVehicleSelected
    ? sortedChronology.map((item) => {
        const camId = resolveCameraId(item.cameraName, item.longitude, item.latitude);
        const camConfig = mapProfile.cameras[camId];
        const lng = camConfig?.lng ?? (typeof item.longitude === 'number' ? item.longitude : mapProfile.center[0]);
        const lat = camConfig?.lat ?? (typeof item.latitude === 'number' ? item.latitude : mapProfile.center[1]);
        const shortCamId = camId.replace('c0', '').replace('c', '');

        return {
          id: item.id,
          name: `${item.cameraName} (${item.timestamp})`,
          cameraName: item.cameraName,
          camId,
          shortCamId,
          lng,
          lat,
          statusType: item.statusType,
          plateNumber: item.plateNumber,
          timestamp: item.timestamp,
          ocrConfidence: item.ocrConfidence,
          statusMessage: item.statusMessage,
        };
      })
    : [];

  // Snap route dynamically along real physical street centerlines and curves
  const dynamicRoute: [number, number][] = hasVehicleSelected && validStops.length >= 2
    ? snapTrajectoryToRoads(validStops, mapProfile.roadSegments)
    : [];

  const mapCenter: [number, number] = mapProfile.center;

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto pb-6 select-none font-body bg-[#000000]">
      {/* Top Search & Time Window Filter Bar */}
      <div className="bg-[#151515] rounded-[3px] p-4 space-y-3 relative z-30">
        <div className="flex items-center justify-between gap-4">
          {/* Search Field */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-2xl">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={isCbe ? "Search Vehicle Plate (e.g. TN47A1507, TN38BE5544) or ID" : "Search Vehicle ID (e.g. 334, 396, 336, 420) or Plate Number"}
              className="w-full bg-[#000000] focus:border-[#F2D04E] text-white placeholder-[#A0A0A0] text-sm rounded-[3px] py-3 pl-4 pr-16 outline-none font-body transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-10 top-1/2 -translate-y-1/2 p-1 text-[#A0A0A0] hover:text-white transition-colors text-xs"
                title="Clear Selection"
              >
                ✕
              </button>
            )}
            <button
              type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:opacity-80 transition-opacity"
              title="Search Plate or Vehicle ID"
            >
              <img src="/assets/search.svg" alt="Search Icon" className="w-5 h-5 text-[#F2D04E]" />
            </button>
          </form>

          {/* Filter Box Button */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="outline-none focus:outline-none flex items-center justify-center cursor-pointer"
              title="Filter"
            >
              <img
                src={isFilterOpen ? "/assets/filter_opened.svg" : "/assets/filter.svg"}
                alt="Filter"
                className="h-10 w-auto object-contain"
              />
            </button>

            {/* Filter Dropdown Popup Menu */}
            {isFilterOpen && (
              <div 
                className="absolute right-0 mt-3 w-64 md:w-72 bg-[#000000] rounded-[3px] z-50 p-4 space-y-4 text-xs font-body"
                style={{ boxShadow: '0px 14px 35px rgba(0, 0, 0, 0.3)' }}
              >
                {/* 1. Timestamp Category */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    Timestamp
                  </h4>
                  {['24 hrs ago', '12 hrs ago', '6 hrs ago'].map((item) => {
                    const isChecked = selectedTimestamps.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedTimestamps, setSelectedTimestamps, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>

                <div className="border-b border-[#AEA793]" />

                {/* 2. Location Category */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    Location
                  </h4>
                  {['Camera 020 (University Ave & Walnut)', 'Camera 023 (University Ave & Nevada)', 'Camera 028 (Grandview Roundabout)', 'Camera 029 (University Ave & Alta Pl)'].map((item) => {
                    const isChecked = selectedLocations.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedLocations, setSelectedLocations, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Dynamic Suggestion Chips for Multi-Camera Trajectories */}
        <div className="flex items-center gap-2 overflow-x-auto text-xs pt-1 no-scrollbar">
          <span className="text-[#AEA793] font-semibold text-[11px] uppercase tracking-wider whitespace-nowrap">
            Cross-Camera Paths:
          </span>
          {crossCameraPaths.map((path) => {
            const isSelected = searchQuery === path.vehicle_id || data.searchedPlate === path.vehicle_id;
            return (
              <button
                key={path.vehicle_id}
                type="button"
                onClick={() => {
                  if (isSelected) {
                    handleClearSearch();
                  } else {
                    setSearchQuery(path.vehicle_id);
                    onSearchPlate && onSearchPlate(path.vehicle_id);
                  }
                }}
                className={`px-2.5 py-1 rounded-[3px] text-xs font-semibold transition-all whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
                  isSelected
                    ? 'bg-[#F2D04E] text-black font-bold shadow-sm'
                    : path.is_corridor
                    ? 'bg-[#1E1E1E] hover:bg-[#2A2A2A] border border-[#F2D04E]/40 text-[#F2D04E]'
                    : 'bg-[#1E1E1E] hover:bg-[#2A2A2A] border border-white/10 text-white/90'
                }`}
                title={`CityFlow Vehicle ${path.vehicle_id} (${path.description})`}
              >
                {path.is_corridor && (
                  <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-black' : 'bg-[#1B7A43]'}`} />
                )}
                <span>{path.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main 2-Column Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-[580px]">
        {/* Left Column: TRACE CHRONOLOGY (5/12 width) */}
        <div className="lg:col-span-5 bg-[#151515] rounded-[3px] p-4 flex flex-col justify-between">
          {/* Header with Title and Badges */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold font-heading text-white tracking-wide">
                TRACE CHRONOLOGY
              </h2>
              <div className="flex items-center gap-2 font-body">
                {/* Scans Badge - Green #1B7A43 */}
                <span className="bg-[#1B7A43] text-[#151515] font-bold text-xs px-3 py-1 rounded-[3px]">
                  {data.totalScans} Scans
                </span>
                {/* Anomaly Badge - Red #971D1B */}
                <span className="bg-[#971D1B] text-[#151515] font-bold text-xs px-3 py-1 rounded-[3px]">
                  {data.totalAnomalies} Anomaly
                </span>
              </div>
            </div>

            {/* Observation Cards List */}
            <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
              {data.chronology.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center text-[#A0A0A0] space-y-3">
                  <div className="w-12 h-12 rounded-full bg-[#1e1e1e] flex items-center justify-center text-[#AEA793]/60">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                  </div>
                  <p className="text-sm font-bold text-white">No Vehicle Observations Found</p>
                  <p className="text-xs text-[#AEA793] max-w-xs leading-relaxed">
                    No trajectory records matched &ldquo;{searchQuery || data.searchedPlate}&rdquo;. Try selecting a cross-camera path above or searching a CityFlow vehicle ID (e.g. 334, 396, 336, 420).
                  </p>
                </div>
              ) : (
                data.chronology.map((item) => {
                  const isAnomaly = item.statusType === 'anomaly';
                  const isBlacklisted = item.statusType === 'blacklisted';
                  const isWarning = isAnomaly || isBlacklisted;

                  return (
                    <div
                      key={item.id}
                      className="bg-[#000000] rounded-[3px] p-3.5 flex flex-col justify-between"
                    >
                      {/* Top Row: Plate, Timestamp, Confidence */}
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-sm text-white font-body tracking-wide">
                            {item.plateNumber}
                          </span>
                          <span className="text-xs text-[#A0A0A0] font-body">
                            {item.timestamp}
                          </span>
                        </div>
                        <span className="text-xs font-bold text-[#1B7A43] font-body">
                          {item.ocrConfidence}%
                        </span>
                      </div>

                      {/* Sub Row: Camera & Location & Side Arrow */}
                      <div className="flex items-center justify-between text-xs text-[#A0A0A0] font-body mb-2">
                        <div className="flex items-center gap-1.5">
                          <svg width="14" height="14" viewBox="0 0 20 19" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5">
                            <path d="M16.3235 12.8229L14.3235 11.6647L18 8.90284L20 10.061L16.3235 12.8229ZM10.5294 9.88286L14.3529 7.03189L5.08824 1.74573L2.88235 5.51732L10.5294 9.88286ZM0 19V17.2181H6.17647V9.43739L2 7.06159C1.56726 6.80501 1.28755 6.43893 1.16088 5.96338C1.03402 5.48782 1.09804 5.03226 1.35294 4.5967L3.55882 0.884505C3.81373 0.468739 4.17157 0.196512 4.63235 0.0678227C5.09314 -0.0608666 5.52941 -0.00642109 5.94118 0.231159L17.5588 6.85371L10.6471 11.9914L7.94118 10.4471V17.2181C7.94118 17.7082 7.76843 18.1276 7.42294 18.4764C7.07726 18.8255 6.66176 19 6.17647 19H0Z" fill="#AEA793"/>
                          </svg>
                          <span>{item.cameraName} ({item.location})</span>
                        </div>
                        <img src="/assets/side_arrow.svg" alt="Side Arrow" className="w-2.5 h-3.5" />
                      </div>

                      {/* Bottom Status Tag Line */}
                      <div className="text-[11px] font-medium font-body">
                        {isWarning ? (
                          <span className="text-[#971D1B] font-semibold">
                            {item.statusMessage}
                          </span>
                        ) : (
                          <span className="text-[#B8860B] font-medium">
                            {item.trackedTimeAgo}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: GIS ROUTE MAP (7/12 width) */}
        <div className="lg:col-span-7 bg-[#151515] rounded-[3px] p-4 flex flex-col justify-between relative overflow-hidden min-h-[500px]">
          {/* Top Map Status / Route Summary Row (Plain informational text, no marker-colour legends) */}
          <div className="flex items-center justify-between mb-3 z-10 select-none flex-wrap gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-[#AEA793] font-semibold uppercase tracking-wider">
                {isCbe ? 'Coimbatore Grid (Cameras 20, 23, 28, 29)' : 'CityFlow Grid (Cameras 20, 23, 28, 29)'}
              </span>
            </div>

            {/* Trajectory Route Status Informational Text */}
            {hasVehicleSelected && dynamicRoute.length >= 2 ? (
              <span className="bg-[#1E1E1E] border border-white/15 text-white/90 text-[11px] font-medium px-3 py-1 rounded-[3px]">
                Cross-Camera Route: {validStops.map(s => s.shortCamId).join(' → ')} ({validStops.length} Camera Sightings)
              </span>
            ) : hasVehicleSelected && validStops.length === 1 ? (
              <span className="bg-[#1E1E1E] border border-white/10 text-[#AEA793] text-[11px] font-medium px-2.5 py-1 rounded-[3px]">
                Single Camera Sighting at Camera {validStops[0].shortCamId}
              </span>
            ) : (
              <span className="bg-[#1E1E1E] border border-white/10 text-[#777777] text-[11px] font-medium px-2.5 py-1 rounded-[3px]">
                No Vehicle Selected
              </span>
            )}
          </div>

          {/* Map Display Surface (MapCN Route Map) */}
          <div className="relative flex-1 bg-[#000000] rounded-[3px] overflow-hidden h-[450px] min-h-[450px]">
            <Map 
              center={mapCenter} 
              zoom={mapProfile.zoom} 
              key={`trace-map-${mapProfile.id}-${activeDataset}`} 
              className="h-full w-full rounded-[3px]"
            >
              {hasVehicleSelected && dynamicRoute.length >= 2 && (
                <MapRoute coordinates={dynamicRoute} color="#F2D04E" width={4} opacity={0.85} />
              )}

              {/* Exactly Four Camera Markers Labelled: 20, 23, 28, 29 */}
              {Object.values(mapProfile.cameras).map((cam) => {
                const shortNum = cam.id.replace('c0', '').replace('c', '');
                const isStartingCam = hasVehicleSelected && startingCameraId === cam.id;
                const obs = validStops.find(s => s.camId === cam.id);

                return (
                  <MapMarker 
                    key={`cam-marker-${cam.id}-${mapProfile.id}`} 
                    longitude={cam.lng} 
                    latitude={cam.lat}
                    anchor="center"
                  >
                    <MarkerContent>
                      <div
                        className={`flex size-7 items-center justify-center rounded-full border-2 border-white shadow-lg transition-transform hover:scale-125 cursor-pointer ${
                          isStartingCam 
                            ? 'bg-[#1B7A43] text-white font-bold' 
                            : 'bg-[#F2D04E] text-black font-bold'
                        } text-xs`}
                        title={cam.name}
                      >
                        {shortNum}
                      </div>
                    </MarkerContent>
                    <MarkerTooltip>
                      <div className="text-xs p-2 space-y-1 bg-[#151515] text-white rounded border border-white/20 shadow-xl max-w-xs">
                        <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-1">
                          <span className="font-bold text-[#F2D04E]">{cam.name}</span>
                          <span className="text-[10px] text-[#A0A0A0] font-mono">{cam.id.toUpperCase()}</span>
                        </div>
                        {obs ? (
                          <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] pt-1">
                            <span className="text-[#A0A0A0]">Plate:</span>
                            <span className="font-bold text-white">{obs.plateNumber}</span>
                            <span className="text-[#A0A0A0]">Timestamp:</span>
                            <span className="text-white">{obs.timestamp}</span>
                            <span className="text-[#A0A0A0]">OCR Conf:</span>
                            <span className="text-[#1B7A43] font-bold">{obs.ocrConfidence}%</span>
                            <span className="text-[#A0A0A0]">Status:</span>
                            <span className={obs.statusType === 'blacklisted' || obs.statusType === 'anomaly' ? 'text-[#971D1B] font-bold' : 'text-[#F2D04E] font-medium'}>
                              {obs.statusType.toUpperCase()}
                            </span>
                            {obs.statusMessage && (
                              <>
                                <span className="text-[#A0A0A0]">Details:</span>
                                <span className="text-[#A0A0A0] truncate">{obs.statusMessage}</span>
                              </>
                            )}
                          </div>
                        ) : (
                          <p className="text-[10px] text-[#888888] italic pt-1">No sightings for selected vehicle</p>
                        )}
                        <p className="text-[10px] text-[#A0A0A0] pt-1 border-t border-white/10">{cam.location}</p>
                      </div>
                    </MarkerTooltip>
                  </MapMarker>
                );
              })}
            </Map>
          </div>
        </div>
      </div>
    </div>
  );
};
