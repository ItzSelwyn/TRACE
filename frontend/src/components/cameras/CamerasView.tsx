import React, { useState } from 'react';
import {
  Map,
  MapMarker,
  MarkerContent,
  MarkerPopup,
  MarkerTooltip,
} from '@/components/ui/map';

export interface CameraMapNode {
  id: string;
  name: string;
  location: string;
  status: 'ONLINE' | 'DOWN';
  lng: number;
  lat: number;
  resolution: string;
  fps: number;
  lastActive: string;
  uptime?: string;
}

export const CamerasView: React.FC = () => {
  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isFilterOpen, setIsFilterOpen] = useState<boolean>(false);
  const [selectedLocation, setSelectedLocation] = useState<string>('North Highway 14');
  const [selectedTimestamp, setSelectedTimestamp] = useState<string>('6 hrs ago');

  // 8 Camera Nodes on Map
  const cameraNodes: CameraMapNode[] = [
    {
      id: 'cam-1',
      name: 'Camera 01',
      location: 'Grand Street & Chrystie St',
      status: 'ONLINE',
      lng: -73.992,
      lat: 40.718,
      resolution: '1080P',
      fps: 30,
      lastActive: 'Live',
      uptime: '6 hrs',
    },
    {
      id: 'cam-2',
      name: 'Camera 02',
      location: 'Grand Street Corridor',
      status: 'ONLINE',
      lng: -73.996,
      lat: 40.716,
      resolution: '1080P',
      fps: 30,
      lastActive: 'Live',
      uptime: '6 hrs',
    },
    {
      id: 'cam-14',
      name: 'Camera 14',
      location: 'North Highway 15',
      status: 'ONLINE',
      lng: -73.982,
      lat: 40.722,
      resolution: '1080P',
      fps: 30,
      lastActive: 'Live',
      uptime: '6 hrs',
    },
    {
      id: 'cam-4',
      name: 'Camera 04',
      location: 'Elizabeth Street & Canal',
      status: 'ONLINE',
      lng: -73.988,
      lat: 40.715,
      resolution: '1080P',
      fps: 30,
      lastActive: 'Live',
      uptime: '6 hrs',
    },
    {
      id: 'cam-5',
      name: 'Camera 05',
      location: 'Mott Street Crossing',
      status: 'ONLINE',
      lng: -73.991,
      lat: 40.713,
      resolution: '1080P',
      fps: 30,
      lastActive: 'Live',
      uptime: '6 hrs',
    },
    {
      id: 'cam-6',
      name: 'Camera 06',
      location: 'Mulberry Street Junction',
      status: 'ONLINE',
      lng: -73.998,
      lat: 40.714,
      resolution: '1080P',
      fps: 30,
      lastActive: 'Live',
      uptime: '6 hrs',
    },
    {
      id: 'cam-15',
      name: 'Camera 15',
      location: 'North Highway 14',
      status: 'DOWN',
      lng: -73.978,
      lat: 40.712,
      resolution: 'Offline',
      fps: 0,
      lastActive: '12 mins ago',
      uptime: '6 hrs',
    },
    {
      id: 'cam-8',
      name: 'Camera 08',
      location: 'Bowery & Bayard Street',
      status: 'DOWN',
      lng: -73.981,
      lat: 40.709,
      resolution: 'Offline',
      fps: 0,
      lastActive: '45 mins ago',
      uptime: '6 hrs',
    },
  ];

  const cameraFootages = [
    {
      id: 'feed-1',
      title: '12-02-2026 Wed 05:02:43pm (C16)',
      src: '/assets/camera_feed_1.png',
      location: 'North Highway 16',
    },
    {
      id: 'feed-2',
      title: '11-03-2026 Thur 04:01:12pm (C15)',
      src: '/assets/camera_feed_2.png',
      location: 'North Highway 15',
    },
    {
      id: 'feed-3',
      title: '11-03-2026 Thur 04:01:12pm (C15)',
      src: '/assets/camera_feed_3.png',
      location: 'North Highway 14',
    },
    {
      id: 'feed-4',
      title: '11-03-2026 Thur 04:01:12pm (C15)',
      src: '/assets/camera_feed_4.png',
      location: 'North Highway 13',
    },
  ];

  const filteredFootages = cameraFootages.filter((feed) => {
    if (searchQuery.trim() === '') return true;
    return (
      feed.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      feed.location.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  const totalCameras = 8;
  const activeCameras = 4;
  const downCameras = 2;
  const uptimeHours = 28;

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-6 select-none font-body relative">
      {/* ================= 1. TOP METRICS CARDS ROW (No strokes, corner radius 3) ================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: TOTAL CAMERAS */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-white uppercase tracking-wider">
            TOTAL CAMERAS
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-white">
            {totalCameras}
          </span>
        </div>

        {/* Card 2: CAMERAS ACTIVE (#1B7A43 Green) */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-[#1B7A43] uppercase tracking-wider">
            CAMERAS ACTIVE
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-[#1B7A43]">
            {activeCameras}
          </span>
        </div>

        {/* Card 3: CAMERAS DOWN (#971D1B Red) */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-[#971D1B] uppercase tracking-wider">
            CAMERAS DOWN
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-[#971D1B]">
            {downCameras}
          </span>
        </div>

        {/* Card 4: UPTIME */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-[#F2D04E] uppercase tracking-wider">
            UPTIME
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-[#F2D04E]">
            {uptimeHours} hrs
          </span>
        </div>
      </div>

      {/* ================= 2. MAIN GIS CAMERA MAP CONTAINER (No strokes, corner radius 3, non-blinking markers, click for details) ================= */}
      <div className="relative rounded-[3px] overflow-hidden bg-[#151515] h-[560px] w-full">
        <Map center={[-73.986, 40.716]} zoom={13.5}>
          {cameraNodes.map((cam) => {
            const isOnline = cam.status === 'ONLINE';

            return (
              <MapMarker key={cam.id} longitude={cam.lng} latitude={cam.lat}>
                <MarkerContent>
                  <div className="relative cursor-pointer transition-transform hover:scale-110">
                    <img
                      src={isOnline ? '/assets/active_camera_marker.svg' : '/assets/down_camera_marker.svg'}
                      alt={cam.name}
                      className="w-7 h-9 object-contain"
                    />
                    {isOnline && (
                      <span className="absolute top-1 left-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-[#1B7A43]" />
                    )}
                  </div>
                </MarkerContent>
                <MarkerTooltip>{cam.name} ({cam.location})</MarkerTooltip>
                <MarkerPopup>
                  <div className="bg-[#000000] p-3 rounded-[3px] w-48 text-left space-y-1 select-none font-body">
                    <div className="font-bold text-white text-sm font-body tracking-wide">
                      {cam.name}
                    </div>
                    <div className="flex items-center gap-1.5 text-[11px] text-[#A0A0A0] mt-1 mb-2 font-body">
                      <img
                        src="/assets/camera_location_icon.svg"
                        alt="location"
                        className="w-3 h-3 object-contain shrink-0 opacity-80"
                      />
                      <span className="truncate">{cam.location}</span>
                    </div>
                    <div className="space-y-1 text-[11px] border-t border-[#AEA793]/30 pt-1.5 font-body">
                      <div className="flex justify-between items-center text-[#A0A0A0]">
                        <span>Uptime</span>
                        <span className="text-white/90">{cam.uptime || '6 hrs'}</span>
                      </div>
                      <div className="flex justify-between items-center text-[#A0A0A0]">
                        <span>Status</span>
                        <span className={`font-semibold ${isOnline ? 'text-[#1B7A43]' : 'text-[#971D1B]'}`}>
                          {isOnline ? 'Active' : 'Down'}
                        </span>
                      </div>
                    </div>
                  </div>
                </MarkerPopup>
              </MapMarker>
            );
          })}
        </Map>
      </div>

      {/* ================= 3. SEARCH & FILTER CONTROLS BAR (No strokes, corner radius 3) ================= */}
      <div className="bg-[#151515] rounded-[3px] p-4 relative z-30 flex flex-col sm:flex-row items-center gap-4">
        {/* Search Bar */}
        <div className="flex-1 w-full relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Camera (e.g. TN 37 CY 1234)"
            className="w-full bg-[#0D0D0D] text-white placeholder-[#808080] text-sm font-body px-4 py-3 rounded-[3px] outline-none pr-10"
          />
          <img
            src="/assets/camera_search_icon.svg"
            alt="Search"
            className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 object-contain"
          />
        </div>

        {/* Filter Toggle Button & Dropdown */}
        <div className="relative w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            className="outline-none focus:outline-none flex items-center justify-center cursor-pointer"
            title="Filter"
          >
            <img
              src={isFilterOpen ? "/assets/alert_filter_opened.svg" : "/assets/alert_filter.svg"}
              alt="Filter"
              className="h-10 w-auto object-contain"
            />
          </button>

          {/* Filter Dropdown Drawer (No stroke, Hanken Grotesk, #AEA793 divider, no bg box change on selection, custom tick.svg) */}
          {isFilterOpen && (
            <div 
              className="absolute right-0 top-full mt-2 w-64 bg-[#000000] rounded-[3px] p-4 z-40 space-y-4 font-body"
              style={{ boxShadow: '0px 14px 35px rgba(0, 0, 0, 0.3)' }}
            >
              {/* Timestamp Category */}
              <div>
                <h4 className="text-xs font-bold font-body text-white uppercase tracking-wider mb-2">
                  Timestamp
                </h4>
                <div className="space-y-1.5 text-xs font-body">
                  {['24 hrs ago', '12 hrs ago', '6 hrs ago'].map((ts) => (
                    <div
                      key={ts}
                      onClick={() => setSelectedTimestamp(ts)}
                      className="cursor-pointer py-1.5 px-1 flex items-center justify-between text-[#AEA793] hover:text-white"
                    >
                      <span>{ts}</span>
                      {selectedTimestamp === ts && (
                        <img src="/assets/tick.svg" alt="Tick" className="w-3.5 h-3 object-contain" />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Horizontal Divider in #AEA793 */}
              <div className="border-b border-[#AEA793]" />

              {/* Location Category */}
              <div>
                <h4 className="text-xs font-bold font-body text-white uppercase tracking-wider mb-2">
                  Location
                </h4>
                <div className="space-y-1.5 text-xs font-body">
                  {[
                    'North Highway 16',
                    'North Highway 15',
                    'North Highway 14',
                    'North Highway 13',
                  ].map((loc) => (
                    <div
                      key={loc}
                      onClick={() => setSelectedLocation(loc)}
                      className="cursor-pointer py-1.5 px-1 flex items-center justify-between text-[#AEA793] hover:text-white"
                    >
                      <span>{loc}</span>
                      {selectedLocation === loc && (
                        <img src="/assets/tick.svg" alt="Tick" className="w-3.5 h-3 object-contain" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ================= 4. CAMERA FOOTAGES SECTION (No strokes, corner radius 3) ================= */}
      <div className="bg-[#151515] rounded-[3px] p-5 space-y-4">
        {/* Title Header */}
        <div className="flex items-center gap-2.5">
          <img
            src="/assets/camera_heading_icon.svg"
            alt="Camera Icon"
            className="w-5 h-5 object-contain"
          />
          <h3 className="text-base md:text-lg font-bold font-body text-white uppercase tracking-wider">
            CAMERA FOOTAGES
          </h3>
        </div>

        {/* 2x2 Video Feed Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredFootages.map((feed) => (
            <div
              key={feed.id}
              className="relative rounded-[3px] overflow-hidden bg-black group"
            >
              <img
                src={feed.src}
                alt={feed.title}
                className="w-full h-auto object-cover block"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
