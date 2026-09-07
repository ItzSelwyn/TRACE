import React, { useState, useEffect } from 'react';
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

const DEFAULT_CAMERAS: CameraMapNode[] = [
  {
    id: 'c020',
    name: 'Camera 020 (W Locust & Grandview)',
    location: 'W Locust & Grandview',
    status: 'ONLINE',
    lng: -90.6865,
    lat: 42.5039,
    resolution: '1080P',
    fps: 10,
    lastActive: 'Live',
    uptime: '28 hrs',
  },
  {
    id: 'c023',
    name: 'Camera 023 (Grandview & Delhi)',
    location: 'Grandview & Delhi',
    status: 'ONLINE',
    lng: -90.6784,
    lat: 42.5055,
    resolution: '1080P',
    fps: 10,
    lastActive: 'Live',
    uptime: '28 hrs',
  },
  {
    id: 'c029',
    name: 'Camera 029 (N Grandview & University)',
    location: 'N Grandview & University',
    status: 'ONLINE',
    lng: -90.6710,
    lat: 42.5085,
    resolution: '1080P',
    fps: 10,
    lastActive: 'Live',
    uptime: '28 hrs',
  },
  {
    id: 'c035',
    name: 'Camera 035 (Highway 20 Corridor)',
    location: 'Highway 20 Corridor',
    status: 'ONLINE',
    lng: -90.6635,
    lat: 42.5115,
    resolution: '1080P',
    fps: 10,
    lastActive: 'Live',
    uptime: '28 hrs',
  },
];

export const CamerasView: React.FC = () => {
  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isFilterOpen, setIsFilterOpen] = useState<boolean>(false);
  const [selectedLocation, setSelectedLocation] = useState<string>('All Locations');
  const [selectedTimestamp, setSelectedTimestamp] = useState<string>('6 hrs ago');

  // Dynamic Camera & Metrics State
  const [cameras, setCameras] = useState<CameraMapNode[]>(DEFAULT_CAMERAS);
  const [metrics, setMetrics] = useState({
    total: 4,
    active: 4,
    down: 0,
    uptimeHours: 28,
  });

  useEffect(() => {
    let isMounted = true;
    const fetchCameraData = async () => {
      try {
        const res = await fetch('/perception/cameras');
        if (!res.ok) return;
        const data = await res.json();
        if (!isMounted || !data.cameras || data.cameras.length === 0) return;

        const mapped: CameraMapNode[] = data.cameras.map((c: any) => ({
          id: c.camera_id,
          name: c.name || `Camera ${c.camera_id.toUpperCase()}`,
          location: c.location || 'CityFlow S04 Corridor',
          status: (c.status === 'ONLINE' || c.status === 'PROCESSING' || c.status === 'SYNC DISABLED') ? 'ONLINE' : 'DOWN',
          lng: typeof c.longitude === 'number' ? c.longitude : -90.675,
          lat: typeof c.latitude === 'number' ? c.latitude : 42.507,
          resolution: c.resolution || '1080P',
          fps: Math.round(c.fps || 10),
          lastActive: 'Live',
          uptime: `${data.uptime_hours || 28} hrs`,
        }));

        setCameras(mapped);
        setMetrics({
          total: data.total_cameras ?? mapped.length,
          active: data.active_cameras ?? mapped.filter(c => c.status === 'ONLINE').length,
          down: data.down_cameras ?? mapped.filter(c => c.status !== 'ONLINE').length,
          uptimeHours: data.uptime_hours ?? 28,
        });
      } catch (err) {
        console.warn('Using default camera metadata:', err);
      }
    };

    fetchCameraData();
    const interval = setInterval(fetchCameraData, 4000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const filteredCameras = cameras.filter((cam) => {
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch =
      q === '' ||
      cam.name.toLowerCase().includes(q) ||
      cam.location.toLowerCase().includes(q) ||
      cam.id.toLowerCase().includes(q);

    const matchesLocation =
      selectedLocation === 'All Locations' ||
      cam.location.toLowerCase().includes(selectedLocation.toLowerCase()) ||
      cam.name.toLowerCase().includes(selectedLocation.toLowerCase());

    return matchesSearch && matchesLocation;
  });

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-6 select-none font-body relative">
      {/* ================= 1. TOP METRICS CARDS ROW (Dynamic Values) ================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: TOTAL CAMERAS */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-white uppercase tracking-wider">
            TOTAL CAMERAS
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-white">
            {metrics.total}
          </span>
        </div>

        {/* Card 2: CAMERAS ACTIVE (#1B7A43 Green) */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-[#1B7A43] uppercase tracking-wider">
            CAMERAS ACTIVE
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-[#1B7A43]">
            {metrics.active}
          </span>
        </div>

        {/* Card 3: CAMERAS DOWN (#971D1B Red) */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-[#971D1B] uppercase tracking-wider">
            CAMERAS DOWN
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-[#971D1B]">
            {metrics.down}
          </span>
        </div>

        {/* Card 4: UPTIME */}
        <div className="bg-[#1E1E1E] rounded-[3px] p-5 flex flex-col justify-between h-32">
          <span className="text-sm font-bold font-body text-[#F2D04E] uppercase tracking-wider">
            UPTIME
          </span>
          <span className="text-4xl md:text-5xl font-bold font-body text-[#F2D04E]">
            {metrics.uptimeHours} hrs
          </span>
        </div>
      </div>

      {/* ================= 2. MAIN GIS CAMERA MAP CONTAINER (Dubuque CityFlow Corridor) ================= */}
      <div className="relative rounded-[3px] overflow-hidden bg-[#151515] h-[560px] w-full">
        <Map center={[-90.675, 42.507]} zoom={13.8}>
          {cameras.map((cam) => {
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
                  <div className="bg-[#161616] p-3 rounded-[3px] w-52 text-left space-y-1 select-none font-body">
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
                        <span>Resolution</span>
                        <span className="text-white/90">{cam.resolution}</span>
                      </div>
                      <div className="flex justify-between items-center text-[#A0A0A0]">
                        <span>Frame Rate</span>
                        <span className="text-white/90">{cam.fps} FPS</span>
                      </div>
                      <div className="flex justify-between items-center text-[#A0A0A0]">
                        <span>Uptime</span>
                        <span className="text-white/90">{cam.uptime || '28 hrs'}</span>
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

      {/* ================= 3. SEARCH & FILTER CONTROLS BAR ================= */}
      <div className="bg-[#151515] rounded-[3px] p-4 relative z-30 flex flex-col sm:flex-row items-center gap-4">
        {/* Search Bar */}
        <div className="flex-1 w-full relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Camera (e.g. Camera 020, Grandview, c023)"
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

          {/* Filter Dropdown Drawer */}
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

              {/* Horizontal Divider */}
              <div className="border-b border-[#AEA793]" />

              {/* Location Category */}
              <div>
                <h4 className="text-xs font-bold font-body text-white uppercase tracking-wider mb-2">
                  Location
                </h4>
                <div className="space-y-1.5 text-xs font-body">
                  {[
                    'All Locations',
                    'W Locust & Grandview',
                    'Grandview & Delhi',
                    'N Grandview & University',
                    'Highway 20 Corridor',
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

      {/* ================= 4. CAMERA FOOTAGES SECTION (Live Camera Video Feeds) ================= */}
      <div className="bg-[#151515] rounded-[3px] p-5 space-y-4">
        {/* Title Header */}
        <div className="flex items-center gap-2.5">
          <img
            src="/assets/camera_heading_icon.svg"
            alt="Camera Icon"
            className="w-5 h-5 object-contain"
          />
          <h3 className="text-base md:text-lg font-bold font-body text-white uppercase tracking-wider">
            CAMERA FOOTAGES (LIVE FEEDS)
          </h3>
        </div>

        {/* 2x2 Live Video Feed Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCameras.map((cam, idx) => (
            <div
              key={cam.id}
              className="relative rounded-[3px] overflow-hidden bg-black group aspect-video flex items-center justify-center border border-white/5"
            >
              {/* Native Live MJPEG Video Stream (No YOLO annotations) */}
              <img
                src={`/perception/camera/${cam.id.toLowerCase()}/feed`}
                alt={cam.name}
                className="w-full h-full object-cover block"
                onError={(e) => {
                  e.currentTarget.src = `/assets/camera_feed_${(idx % 4) + 1}.png`;
                }}
              />

              {/* LIVE Indicator Tag */}
              <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-black/70 backdrop-blur-sm px-2.5 py-1 rounded-[3px] border border-white/10 select-none">
                <span className="w-2 h-2 rounded-full bg-[#1B7A43] animate-pulse" />
                <span className="text-[10px] font-bold text-white uppercase tracking-wider font-body">LIVE</span>
              </div>

              {/* Camera Info Overlay */}
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/85 via-black/45 to-transparent p-3 flex items-center justify-between text-xs font-body select-none">
                <div>
                  <p className="font-bold text-white tracking-wide text-sm">{cam.name}</p>
                  <p className="text-[11px] text-[#AEA793]">{cam.location}</p>
                </div>
                <span className="text-[10px] bg-[#1E1E1E] text-[#F2D04E] font-semibold px-2 py-0.5 rounded-[3px] border border-[#F2D04E]/30">
                  {cam.resolution} • {cam.fps} FPS
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
