import React, { useState } from 'react';
import { VehicleTraceDataPayload } from '../../types/vehicleTrace';
import {
  Map,
  MapMarker,
  MarkerContent,
  MarkerTooltip,
  MapRoute,
} from "@/components/ui/map";

interface VehicleTraceViewProps {
  data: VehicleTraceDataPayload;
  onSearchPlate?: (plateQuery: string) => void;
}

export const VehicleTraceView: React.FC<VehicleTraceViewProps> = ({ 
  data, 
  onSearchPlate 
}) => {
  const [searchQuery, setSearchQuery] = useState(data.searchedPlate || '');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedTimestamps, setSelectedTimestamps] = useState<string[]>(['24 hrs ago']);

  // Keep search input synced if searchedPlate updates from parent
  React.useEffect(() => {
    setSearchQuery(data.searchedPlate || '');
  }, [data.searchedPlate]);
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
    if (onSearchPlate && searchQuery.trim()) {
      onSearchPlate(searchQuery.trim());
    }
  };

  // Extract route coordinates and stops dynamically from chronology
  const validStops = data.chronology
    .filter((item) => typeof item.longitude === 'number' && typeof item.latitude === 'number')
    .map((item) => ({
      name: `${item.cameraName} (${item.timestamp})`,
      lng: item.longitude as number,
      lat: item.latitude as number,
      statusType: item.statusType,
      plateNumber: item.plateNumber,
    }));

  const dynamicRoute: [number, number][] = [];
  validStops.forEach((stop) => {
    const last = dynamicRoute[dynamicRoute.length - 1];
    if (!last || last[0] !== stop.lng || last[1] !== stop.lat) {
      dynamicRoute.push([stop.lng, stop.lat]);
    }
  });

  const mapCenter: [number, number] = validStops.length > 0
    ? [validStops[0].lng, validStops[0].lat]
    : [-90.675, 42.507];

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
              placeholder="Search Plate (e.g. TN 37 CY 1234) or Vehicle ID (e.g. 260, 261, 272, TRK-001)"
              className="w-full bg-[#000000] focus:border-[#F2D04E] text-white placeholder-[#A0A0A0] text-sm rounded-[3px] py-3 pl-4 pr-12 outline-none font-body transition-all"
            />
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
                  {['Camera 020 (W Locust & Grandview)', 'Camera 023 (Grandview & Delhi)', 'Camera 029 (N Grandview & University)', 'Camera 035 (Highway 20 Corridor)'].map((item) => {
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

        {/* Quick Suggestion Chips for Multi-Camera Trajectories */}
        <div className="flex items-center gap-2 overflow-x-auto text-xs pt-1">
          <span className="text-[#AEA793] font-semibold text-[11px] uppercase tracking-wider whitespace-nowrap">
            Cross-Camera Paths:
          </span>
          <button
            type="button"
            onClick={() => { setSearchQuery('260'); onSearchPlate && onSearchPlate('260'); }}
            className={`px-2.5 py-1 rounded-[3px] text-xs font-semibold transition-all whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
              searchQuery === '260'
                ? 'bg-[#F2D04E] text-black font-bold'
                : 'bg-[#1E1E1E] hover:bg-[#2A2A2A] border border-[#F2D04E]/40 text-[#F2D04E]'
            }`}
            title="CityFlow Vehicle 260 (Crosses all 4 cameras in corridor)"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#1B7A43]" />
            <span>Vehicle 260 (4-Cam Corridor)</span>
          </button>
          <button
            type="button"
            onClick={() => { setSearchQuery('261'); onSearchPlate && onSearchPlate('261'); }}
            className={`px-2.5 py-1 rounded-[3px] text-xs transition-all whitespace-nowrap cursor-pointer ${
              searchQuery === '261'
                ? 'bg-[#F2D04E] text-black font-bold'
                : 'bg-[#1E1E1E] hover:bg-[#2A2A2A] border border-white/10 text-white/90'
            }`}
            title="CityFlow Vehicle 261 (Camera 020 -> Camera 023)"
          >
            Vehicle 261 (c020 → c023)
          </button>
          <button
            type="button"
            onClick={() => { setSearchQuery('272'); onSearchPlate && onSearchPlate('272'); }}
            className={`px-2.5 py-1 rounded-[3px] text-xs transition-all whitespace-nowrap cursor-pointer ${
              searchQuery === '272'
                ? 'bg-[#F2D04E] text-black font-bold'
                : 'bg-[#1E1E1E] hover:bg-[#2A2A2A] border border-white/10 text-white/90'
            }`}
            title="CityFlow Vehicle 272 (Camera 029 -> Camera 035)"
          >
            Vehicle 272 (c029 → c035)
          </button>
          <button
            type="button"
            onClick={() => { setSearchQuery('TN 37 CY 1234'); onSearchPlate && onSearchPlate('TN 37 CY 1234'); }}
            className={`px-2.5 py-1 rounded-[3px] text-xs transition-all whitespace-nowrap cursor-pointer ${
              searchQuery === 'TN 37 CY 1234'
                ? 'bg-[#F2D04E] text-black font-bold'
                : 'bg-[#1E1E1E] hover:bg-[#2A2A2A] border border-white/10 text-white/90'
            }`}
            title="Plate TN 37 CY 1234 (ANPR Multi-Camera Corridor)"
          >
            TN 37 CY 1234 (ANPR Plate)
          </button>
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
                    No trajectory records matched &ldquo;{searchQuery || data.searchedPlate}&rdquo;. Try searching a valid track ID (e.g. TRK-009) or CityFlow vehicle ID (e.g. 260).
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
          {/* Top Map Legends Overlay Row */}
          <div className="flex items-center justify-between mb-3 z-10 select-none flex-wrap gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Scanned Legend (#1B7A43) */}
              <div className="bg-[#000000] px-3 py-1.5 rounded-[3px] flex items-center gap-2 text-xs font-body text-[#1B7A43]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#1B7A43]" />
                <span>Scanned</span>
              </div>

              {/* Trajectory Legend */}
              <div className="bg-[#000000] px-3 py-1.5 rounded-[3px] flex items-center gap-2 text-xs font-body text-[#F2D04E]">
                <span className="w-4 h-0.5 bg-[#F2D04E]" />
                <span>Trajectory</span>
              </div>

              {/* Anomaly / Blacklisted Legend (#971D1B) */}
              <div className="bg-[#000000] px-3 py-1.5 rounded-[3px] flex items-center gap-2 text-xs font-body text-[#971D1B]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#971D1B]" />
                <span>Anomaly / Blacklisted</span>
              </div>
            </div>

            {/* Trajectory Route Status Badge */}
            {dynamicRoute.length >= 2 ? (
              <span className="bg-[#F2D04E]/10 border border-[#F2D04E]/40 text-[#F2D04E] text-[11px] font-bold px-2.5 py-1 rounded-[3px] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#1B7A43]" />
                <span>Cross-Camera Route ({dynamicRoute.length} Junctions)</span>
              </span>
            ) : validStops.length === 1 ? (
              <span className="bg-white/5 border border-white/15 text-[#AEA793] text-[11px] font-medium px-2.5 py-1 rounded-[3px]">
                Single Camera Detection
              </span>
            ) : (
              <span className="bg-white/5 border border-white/10 text-[#666666] text-[11px] font-medium px-2.5 py-1 rounded-[3px]">
                No Route Points
              </span>
            )}
          </div>

          {/* Map Display Surface (MapCN Route Map) */}
          <div className="relative flex-1 bg-[#000000] rounded-[3px] overflow-hidden h-[450px] min-h-[450px]">
            <Map center={mapCenter} zoom={validStops.length === 1 ? 14.5 : 13.0} className="h-full w-full rounded-[3px]">
              {dynamicRoute.length >= 2 && (
                <MapRoute coordinates={dynamicRoute} color="#F2D04E" width={4} opacity={0.85} />
              )}

              {validStops.map((stop, index) => {
                const isAnomaly = stop.statusType === 'anomaly' || stop.statusType === 'blacklisted';
                return (
                  <MapMarker key={`${stop.name}-${index}`} longitude={stop.lng} latitude={stop.lat}>
                    <MarkerContent>
                      <div
                        className={`flex size-5 items-center justify-center rounded-full border-2 border-white text-[11px] font-bold shadow-lg transition-transform hover:scale-125 ${
                          isAnomaly ? 'bg-[#971D1B] text-white' : index === 0 ? 'bg-[#1B7A43] text-white' : 'bg-[#F2D04E] text-[#151515]'
                        }`}
                      >
                        {index + 1}
                      </div>
                    </MarkerContent>
                    <MarkerTooltip>
                      <div className="text-xs p-1">
                        <p className="font-bold">{stop.plateNumber}</p>
                        <p>{stop.name}</p>
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
