import React, { useState } from 'react';
import { VehicleTraceDataPayload } from '../../types/vehicleTrace';

interface VehicleTraceViewProps {
  data: VehicleTraceDataPayload;
  onSearchPlate?: (plateQuery: string) => void;
}

export const VehicleTraceView: React.FC<VehicleTraceViewProps> = ({ 
  data, 
  onSearchPlate 
}) => {
  const [searchQuery, setSearchQuery] = useState(data.searchedPlate || '');
  const [timeWindow, setTimeWindow] = useState(data.selectedTimeWindow || '24hrs');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearchPlate && searchQuery.trim()) {
      onSearchPlate(searchQuery.trim());
    }
  };

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto pb-6 select-none font-body bg-[#151515]">
      {/* Top Search & Time Window Bar */}
      <div className="bg-[#1E1E1E] rounded-xl p-4 flex items-center justify-between gap-4">
        {/* Search Field */}
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-2xl">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Number Plate (e.g. TN 37 CY 1234)"
            className="w-full bg-[#151515] focus:border-[#F2D04E] text-white placeholder-[#A0A0A0] text-sm rounded-lg py-3 pl-4 pr-12 outline-none font-body transition-all"
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:opacity-80 transition-opacity"
            title="Search Plate"
          >
            <img src="/assets/search.svg" alt="Search Icon" className="w-5 h-5 text-[#F2D04E]" />
          </button>
        </form>

        {/* 24hrs Time Filter Dropdown Button */}
        <div className="relative">
          <button
            className="bg-[#F2D04E] hover:bg-[#F8DF7B] text-black font-bold font-heading text-xs px-4 py-2.5 rounded-lg flex items-center gap-2.5 transition-all shadow-sm"
            title="Select Time Window"
          >
            <span>{timeWindow}</span>
            <img src="/assets/dropdown.svg" alt="Dropdown" className="w-3.5 h-2" />
          </button>
        </div>
      </div>

      {/* Main 2-Column Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-[580px]">
        {/* Left Column: TRACE CHRONOLOGY (5/12 width) */}
        <div className="lg:col-span-5 bg-[#1E1E1E] rounded-xl p-4 flex flex-col justify-between">
          {/* Header with Title and Badges */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold font-heading text-white tracking-wide">
                TRACE CHRONOLOGY
              </h2>
              <div className="flex items-center gap-2 font-heading">
                {/* 5 Scans Badge - Green #1B7A43 background with #151515 text */}
                <span className="bg-[#1B7A43] text-[#151515] font-bold text-xs px-3 py-1 rounded-md">
                  {data.totalScans} Scans
                </span>
                {/* 2 Anomaly Badge - Red #AC251D background with #151515 text */}
                <span className="bg-[#AC251D] text-[#151515] font-bold text-xs px-3 py-1 rounded-md">
                  {data.totalAnomalies} Anomaly
                </span>
              </div>
            </div>

            {/* Observation Cards List */}
            <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
              {data.chronology.map((item) => {
                const isAnomaly = item.statusType === 'anomaly';
                const isBlacklisted = item.statusType === 'blacklisted';
                const isWarning = isAnomaly || isBlacklisted;

                return (
                  <div
                    key={item.id}
                    className="bg-[#151515] hover:bg-[#1A1A1A] rounded-lg p-3.5 flex flex-col justify-between transition-all cursor-pointer group"
                  >
                    {/* Top Row: Plate, Timestamp, Confidence */}
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-sm text-white font-heading tracking-wide">
                          {item.plateNumber}
                        </span>
                        <span className="text-xs text-[#A0A0A0] font-body">
                          {item.timestamp}
                        </span>
                      </div>
                      <span className="text-xs font-bold text-[#1B7A43] font-heading">
                        {item.ocrConfidence}%
                      </span>
                    </div>

                    {/* Sub Row: Camera & Location */}
                    <div className="flex items-center justify-between text-xs text-[#A0A0A0] font-body mb-2">
                      <div className="flex items-center gap-1.5">
                        <img src="/assets/camera.svg" alt="Camera" className="w-3.5 h-3.5 text-[#A0A0A0] opacity-80" />
                        <span>{item.cameraName} ({item.location})</span>
                      </div>
                      <span className="text-sm font-bold text-[#A0A0A0] group-hover:text-white transition-colors">›</span>
                    </div>

                    {/* Bottom Status Tag Line */}
                    <div className="text-[11px] font-medium font-body">
                      {isWarning ? (
                        <span className="text-[#AC251D] font-semibold">
                          {item.statusMessage}
                        </span>
                      ) : (
                        <span className="text-[#F2D04E] font-medium">
                          {item.trackedTimeAgo}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: GIS MAP WITH TRAJECTORY (7/12 width) */}
        <div className="lg:col-span-7 bg-[#1E1E1E] rounded-xl p-4 flex flex-col justify-between relative overflow-hidden min-h-[500px]">
          {/* Top Map Legends Overlay Row */}
          <div className="flex items-center gap-2 mb-3 z-10 select-none flex-wrap">
            {/* Scanned Legend (#1B7A43) */}
            <div className="bg-[#151515] px-3 py-1.5 rounded flex items-center gap-2 text-xs font-body text-[#1B7A43]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#1B7A43]" />
              <span>Scanned</span>
            </div>

            {/* Trajectory Legend */}
            <div className="bg-[#151515] px-3 py-1.5 rounded flex items-center gap-2 text-xs font-body text-[#F2D04E]">
              <span className="w-4 h-0.5 bg-[#F2D04E]" />
              <span>Trajectory</span>
            </div>

            {/* Anomaly / Blacklisted Legend (#AC251D) */}
            <div className="bg-[#151515] px-3 py-1.5 rounded flex items-center gap-2 text-xs font-body text-[#AC251D]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#AC251D]" />
              <span>Anomaly / Blacklisted</span>
            </div>
          </div>

          {/* Map Display Surface */}
          <div className="relative flex-1 bg-[#101010] rounded-lg overflow-hidden flex items-center justify-center">
            <img
              src="/assets/trajectory_map.svg"
              alt="Trajectory GIS Map"
              className="w-full h-full object-cover opacity-80"
            />

            {/* SVG Trajectory Overlay Route Line */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 800 500" preserveAspectRatio="none">
              <path
                d="M 120 180 L 280 270 L 400 370 L 520 370 L 680 430 L 730 390"
                stroke="#F2D04E"
                strokeWidth="4"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="120" cy="180" r="10" fill="#AC251D" stroke="#FFFFFF" strokeWidth="3" />
              <circle cx="680" cy="430" r="10" fill="#1B7A43" stroke="#FFFFFF" strokeWidth="3" />
              <circle cx="730" cy="390" r="10" fill="#AC251D" stroke="#FFFFFF" strokeWidth="3" />
            </svg>

            {/* Zoom Controls */}
            <div className="absolute bottom-4 right-4 flex flex-col bg-[#151515] rounded-md overflow-hidden z-10 shadow-lg">
              <button className="w-8 h-8 flex items-center justify-center text-white hover:bg-[#252525] font-bold text-lg border-b border-[#252525]">
                +
              </button>
              <button className="w-8 h-8 flex items-center justify-center text-white hover:bg-[#252525] font-bold text-lg">
                −
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
