import React, { useState, useEffect } from 'react';
import {
  Map,
  MapMarker,
  MarkerContent,
  MarkerTooltip,
  MarkerPopup,
  MapRoute,
  HeatmapPoint,
} from '@/components/ui/map';
import { ROAD_SEGMENTS } from '@/data/roadGeometry';

export type AnalyticsTab = 'HEATMAP' | 'OD_MATRIX' | 'SEGMENT_DETAIL';
export type TimeFilter = 'LIVE' | '1hr' | '6hrs' | '12hrs' | '24hrs';

export interface TrafficRoadSegment {
  edge_id?: string;
  from_camera_id: string;
  to_camera_id: string;
  name: string;
  density: number;
  congestion_status: 'Optimal' | 'Moderate' | 'Critical' | string;
  avg_speed_kmph: number;
  speed_limit_kmph?: number;
  color?: string;
  vehicle_count?: number;
  coordinates: [number, number][];
}

export interface CameraTrafficStat {
  camera_id: string;
  name: string;
  short_name?: string;
  location: string;
  latitude: number;
  longitude: number;
  vehicle_count: number;
  traffic_density: number;
  congestion_level: string;
  weight: number;
  status_color?: 'red' | 'yellow' | 'green';
  max_capacity?: number;
  avg_speed_kmph?: number;
}

export interface HeatmapResponsePayload {
  corridor_name?: string;
  subtitle?: string;
  cameras_label?: string;
  total_vehicles: number;
  max_capacity: number;
  congestion_index: string;
  avg_corridor_speed?: number;
  segments?: TrafficRoadSegment[];
  camera_stats: CameraTrafficStat[];
  heatmap_points: Array<{ lng: number; lat: number; weight: number }>;
}

export interface ODMatrixResponsePayload {
  corridor_name?: string;
  subtitle?: string;
  zones?: string[];
  matrix?: Record<string, Record<string, number | null>>;
  flow_rate_unit?: string;
  entries?: Array<{ origin_zone: string; destination_zone: string; trip_count: number }>;
}

interface MonitoredSegment {
  id: number;
  title: string;
  shortName: string;
  statusColor: 'red' | 'yellow' | 'green';
  vehiclesTravelling: number;
  maxCapacity: number;
  timestamp: string;
  congestionIndex: string;
  congestionColor: 'red' | 'yellow' | 'green';
  lng: number;
  lat: number;
}

// Live Interactive Chart Component for Segment Details
const SegmentSpeedChart: React.FC<{ filter: TimeFilter; segmentName: string }> = ({ filter, segmentName }) => {
  const [hoveredPoint, setHoveredPoint] = useState<{ time: string; speed: number; x: number; y: number } | null>(null);

  // Dynamic sample data based on time filter & segment congestion
  const getFilterData = () => {
    const isBottleneck = segmentName.includes('028') || segmentName.includes('Roundabout');
    const isModerate = segmentName.includes('023') || segmentName.includes('Nevada');
    // Offset speed to reflect actual flow condition at this camera node
    const offset = isBottleneck ? -25 : isModerate ? -8 : 15;
    const clamp = (val: number) => Math.max(18, Math.min(95, val));

    switch (filter) {
      case 'LIVE':
        return [
          { time: '10:00', speed: clamp(65 + offset) },
          { time: '10:05', speed: clamp(58 + offset) },
          { time: '10:10', speed: clamp(48 + offset) },
          { time: '10:15', speed: clamp(38 + offset) },
          { time: '10:20', speed: clamp(30 + offset) },
          { time: '10:23', speed: clamp(32 + offset) },
        ];
      case '1hr':
        return [
          { time: '09:30', speed: clamp(72 + offset) },
          { time: '09:40', speed: clamp(64 + offset) },
          { time: '09:50', speed: clamp(50 + offset) },
          { time: '10:00', speed: clamp(42 + offset) },
          { time: '10:10', speed: clamp(32 + offset) },
          { time: '10:23', speed: clamp(34 + offset) },
        ];
      case '6hrs':
        return [
          { time: '05:00', speed: clamp(80 + offset) },
          { time: '06:00', speed: clamp(65 + offset) },
          { time: '07:00', speed: clamp(45 + offset) },
          { time: '08:00', speed: clamp(28 + offset) },
          { time: '09:00', speed: clamp(36 + offset) },
          { time: '10:00', speed: clamp(32 + offset) },
        ];
      case '12hrs':
        return [
          { time: '22:00', speed: clamp(88 + offset) },
          { time: '01:00', speed: clamp(90 + offset) },
          { time: '04:00', speed: clamp(82 + offset) },
          { time: '07:00', speed: clamp(42 + offset) },
          { time: '09:00', speed: clamp(30 + offset) },
          { time: '10:23', speed: clamp(32 + offset) },
        ];
      default: // 24hrs
        return [
          { time: '00:00', speed: clamp(80 + offset) },
          { time: '04:00', speed: clamp(85 + offset) },
          { time: '08:00', speed: clamp(38 + offset) },
          { time: '12:00', speed: clamp(44 + offset) },
          { time: '16:00', speed: clamp(28 + offset) },
          { time: '20:00', speed: clamp(62 + offset) },
          { time: '24:00', speed: clamp(78 + offset) },
        ];
    }
  };

  const points = getFilterData();
  const svgWidth = 800;
  const svgHeight = 280;
  const paddingLeft = 50;
  const paddingRight = 30;
  const paddingTop = 25;
  const paddingBottom = 35;

  const chartWidth = svgWidth - paddingLeft - paddingRight;
  const chartHeight = svgHeight - paddingTop - paddingBottom;
  const maxSpeed = 100;

  const coords = points.map((p, i) => {
    const x = paddingLeft + (i / (points.length - 1)) * chartWidth;
    const y = paddingTop + (1 - p.speed / maxSpeed) * chartHeight;
    return { ...p, x, y };
  });

  const pathD = coords.reduce((acc, pt, i, arr) => {
    if (i === 0) return `M ${pt.x} ${pt.y}`;
    const prev = arr[i - 1];
    const cx1 = prev.x + (pt.x - prev.x) / 2;
    const cy1 = prev.y;
    const cx2 = prev.x + (pt.x - prev.x) / 2;
    const cy2 = pt.y;
    return `${acc} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${pt.x} ${pt.y}`;
  }, '');

  const areaD = `${pathD} L ${coords[coords.length - 1].x} ${paddingTop + chartHeight} L ${coords[0].x} ${paddingTop + chartHeight} Z`;
  const yTicks = [100, 80, 60, 40, 20, 0];

  return (
    <div className="w-full relative select-none font-body py-2">
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full h-auto overflow-visible"
        onMouseLeave={() => setHoveredPoint(null)}
      >
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F2D04E" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#F2D04E" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Horizontal Grid lines & Y-Axis Ticks */}
        {yTicks.map((tick) => {
          const y = paddingTop + (1 - tick / maxSpeed) * chartHeight;
          return (
            <g key={tick}>
              <line
                x1={paddingLeft}
                y1={y}
                x2={svgWidth - paddingRight}
                y2={y}
                stroke="#262626"
                strokeWidth="1"
              />
              <text
                x={paddingLeft - 10}
                y={y + 4}
                fill="#808080"
                fontSize="11"
                textAnchor="end"
                className="font-body"
              >
                {tick} km/h
              </text>
            </g>
          );
        })}

        {/* Threshold Critical Reference Line (40 km/h) */}
        <line
          x1={paddingLeft}
          y1={paddingTop + (1 - 40 / maxSpeed) * chartHeight}
          x2={svgWidth - paddingRight}
          y2={paddingTop + (1 - 40 / maxSpeed) * chartHeight}
          stroke="#971D1B"
          strokeWidth="1.5"
          strokeDasharray="4 4"
        />

        {/* Area Gradient Fill */}
        <path d={areaD} fill="url(#chartGradient)" />

        {/* Live Speed Line */}
        <path d={pathD} fill="none" stroke="#F2D04E" strokeWidth="3" strokeLinecap="round" />

        {/* Data Point Circles */}
        {coords.map((pt, i) => (
          <g key={i}>
            <circle
              cx={pt.x}
              cy={pt.y}
              r={pt.speed < 40 ? 5 : 4}
              fill={pt.speed < 40 ? "#971D1B" : "#F2D04E"}
            />
            {/* Interactive Mouse Hover Hit Target */}
            <circle
              cx={pt.x}
              cy={pt.y}
              r="16"
              fill="transparent"
              className="cursor-pointer"
              onMouseEnter={() => setHoveredPoint(pt)}
            />
          </g>
        ))}

        {/* X-Axis Time Labels */}
        {coords.map((pt, i) => (
          <text
            key={i}
            x={pt.x}
            y={svgHeight - 8}
            fill="#808080"
            fontSize="11"
            textAnchor="middle"
            className="font-body"
          >
            {pt.time}
          </text>
        ))}
      </svg>

      {/* Hover Tooltip Card */}
      {hoveredPoint && (
        <div
          className="absolute z-30 bg-[#151515] text-white text-xs px-3 py-1.5 rounded pointer-events-none font-body -translate-x-1/2 -translate-y-full mb-2"
          style={{
            left: `${(hoveredPoint.x / svgWidth) * 100}%`,
            top: `${(hoveredPoint.y / svgHeight) * 100}%`,
          }}
        >
          <div className="font-semibold text-white">{hoveredPoint.time}</div>
          <div className="text-[#F2D04E] font-bold">{hoveredPoint.speed} km/h</div>
        </div>
      )}
    </div>
  );
};

export const AnalyticsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AnalyticsTab>('HEATMAP');
  const [activeFilter, setActiveFilter] = useState<TimeFilter>('LIVE');
  const [selectedSegmentId, setSelectedSegmentId] = useState<number>(1);
  const [exportToast, setExportToast] = useState<string | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapResponsePayload | null>(null);
  const [odMatrixData, setOdMatrixData] = useState<ODMatrixResponsePayload | null>(null);

  // Fetch live heatmap and corridor camera traffic statistics + dynamic OD matrix with 3s live polling
  useEffect(() => {
    let isMounted = true;
    const fetchAnalytics = async () => {
      try {
        const [heatmapRes, odRes] = await Promise.all([
          fetch(`/analytics/heatmap?filter=${activeFilter}`),
          fetch(`/analytics/od-matrix?filter=${activeFilter}`),
        ]);
        if (heatmapRes.ok) {
          const json = await heatmapRes.json();
          if (isMounted) {
            setHeatmapData(json);
          }
        }
        if (odRes.ok) {
          const odJson = await odRes.json();
          if (isMounted) {
            setOdMatrixData(odJson);
          }
        }
      } catch (err) {
        console.error('Failed to fetch analytics data:', err);
      }
    };
    fetchAnalytics();

    // Auto-poll in LIVE mode for dynamic traffic updates from video playback
    let pollTimer: any = null;
    if (activeFilter === 'LIVE') {
      pollTimer = setInterval(fetchAnalytics, 3000);
    }

    return () => {
      isMounted = false;
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [activeFilter]);

  // Default CityFlow S05 road traffic segments connecting the corridor cameras
  const DEFAULT_ROAD_SEGMENTS: TrafficRoadSegment[] = [
    {
      from_camera_id: 'c020',
      to_camera_id: 'c023',
      name: 'University Ave (Walnut to Nevada)',
      density: 22,
      congestion_status: 'Optimal',
      avg_speed_kmph: 56.5,
      color: '#1B7A43',
      vehicle_count: 32,
      coordinates: ROAD_SEGMENTS['c020_c023'] || [],
    },
    {
      from_camera_id: 'c023',
      to_camera_id: 'c028',
      name: 'University Ave (Nevada to Roundabout)',
      density: 26,
      congestion_status: 'Optimal',
      avg_speed_kmph: 53.5,
      color: '#1B7A43',
      vehicle_count: 38,
      coordinates: ROAD_SEGMENTS['c023_c028'] || [],
    },
    {
      from_camera_id: 'c028',
      to_camera_id: 'c029',
      name: 'University Ave (Roundabout to Alta Pl)',
      density: 45,
      congestion_status: 'Moderate',
      avg_speed_kmph: 43.0,
      color: '#F2D04E',
      vehicle_count: 46,
      coordinates: ROAD_SEGMENTS['c028_c029'] || [],
    },
  ];

  const roadSegments: TrafficRoadSegment[] = (heatmapData?.segments && heatmapData.segments.length > 0)
    ? heatmapData.segments.map(seg => ({
        ...seg,
        coordinates: (seg.coordinates && seg.coordinates.length > 1)
          ? seg.coordinates
          : (ROAD_SEGMENTS[`${seg.from_camera_id}_${seg.to_camera_id}`] ||
             ROAD_SEGMENTS[`${seg.from_camera_id.slice(0, 4)}_${seg.to_camera_id.slice(0, 4)}`] ||
             DEFAULT_ROAD_SEGMENTS.find(d => d.name === seg.name)?.coordinates || []),
      }))
    : DEFAULT_ROAD_SEGMENTS;

  // Heatmap Point Data for Maplibre/mapcn fallback
  const heatmapPoints: HeatmapPoint[] = (heatmapData?.heatmap_points && heatmapData.heatmap_points.length > 0)
    ? heatmapData.heatmap_points
    : [
        { lng: -90.688350, lat: 42.498360, weight: 0.35 },
        { lng: -90.681350, lat: 42.499140, weight: 0.32 },
        { lng: -90.675620, lat: 42.499860, weight: 0.28 },
        { lng: -90.693500, lat: 42.499190, weight: 0.55 },
      ];

  // OD Matrix Zones & Data Structure for CityFlow S05 Corridor
  const zones = odMatrixData?.zones || ['CAM-020 (Walnut)', 'CAM-023 (Nevada)', 'CAM-028 (Roundabout)', 'CAM-029 (Alta Pl)'];

  const matrixData: Record<string, Record<string, number | null>> = (odMatrixData?.matrix && Object.keys(odMatrixData.matrix).length > 0)
    ? odMatrixData.matrix
    : {
        'CAM-020 (Walnut)': { 'CAM-020 (Walnut)': null, 'CAM-023 (Nevada)': 165, 'CAM-028 (Roundabout)': 140, 'CAM-029 (Alta Pl)': 95 },
        'CAM-023 (Nevada)': { 'CAM-020 (Walnut)': 150, 'CAM-023 (Nevada)': null, 'CAM-028 (Roundabout)': 175, 'CAM-029 (Alta Pl)': 120 },
        'CAM-028 (Roundabout)': { 'CAM-020 (Walnut)': 135, 'CAM-023 (Nevada)': 170, 'CAM-028 (Roundabout)': null, 'CAM-029 (Alta Pl)': 235 },
        'CAM-029 (Alta Pl)': { 'CAM-020 (Walnut)': 90, 'CAM-023 (Nevada)': 125, 'CAM-028 (Roundabout)': 225, 'CAM-029 (Alta Pl)': null },
      };

  // Monitored Segments List based on dynamic corridor camera stats
  const monitoredSegments: MonitoredSegment[] = (heatmapData?.camera_stats && heatmapData.camera_stats.length > 0)
    ? heatmapData.camera_stats.map((cam, idx) => {
        const color: 'red' | 'yellow' | 'green' = 
          (cam.status_color as any) ||
          (cam.congestion_level === 'Critical' ? 'red' : cam.congestion_level === 'Moderate' ? 'yellow' : 'green');
        return {
          id: idx + 1,
          title: cam.name,
          shortName: cam.short_name || cam.name,
          statusColor: color,
          vehiclesTravelling: cam.vehicle_count,
          maxCapacity: cam.max_capacity || 200,
          timestamp: '10:23:01 am',
          congestionIndex: cam.congestion_level,
          congestionColor: color,
          lng: cam.longitude,
          lat: cam.latitude,
        };
      })
    : [
        {
          id: 1,
          title: 'Camera 020 (University Ave & Walnut)',
          shortName: 'CAM-020 (Walnut)',
          statusColor: 'green',
          vehiclesTravelling: 14,
          maxCapacity: 200,
          timestamp: '10:23:01 am',
          congestionIndex: 'Optimal',
          congestionColor: 'green',
          lng: -90.675620,
          lat: 42.499860,
        },
        {
          id: 2,
          title: 'Camera 023 (University Ave & Nevada)',
          shortName: 'CAM-023 (Nevada)',
          statusColor: 'green',
          vehiclesTravelling: 18,
          maxCapacity: 200,
          timestamp: '10:23:01 am',
          congestionIndex: 'Optimal',
          congestionColor: 'green',
          lng: -90.681350,
          lat: 42.499140,
        },
        {
          id: 3,
          title: 'Camera 028 (Grandview Roundabout)',
          shortName: 'CAM-028 (Roundabout)',
          statusColor: 'green',
          vehiclesTravelling: 20,
          maxCapacity: 240,
          timestamp: '10:23:01 am',
          congestionIndex: 'Optimal',
          congestionColor: 'green',
          lng: -90.688350,
          lat: 42.498360,
        },
        {
          id: 4,
          title: 'Camera 029 (University Ave & Alta Pl)',
          shortName: 'CAM-029 (Alta Pl)',
          statusColor: 'yellow',
          vehiclesTravelling: 26,
          maxCapacity: 200,
          timestamp: '10:23:01 am',
          congestionIndex: 'Moderate',
          congestionColor: 'yellow',
          lng: -90.693500,
          lat: 42.499190,
        },
      ];

  const selectedSegment = monitoredSegments.find((s) => s.id === selectedSegmentId) || monitoredSegments[0];

  // Helper to determine flow type styling for OD matrix
  const getCellStyling = (val: number | null) => {
    if (val === null) {
      return { bg: 'bg-[#151515]', text: 'text-[#666666]', label: '-' };
    }
    const unit = odMatrixData?.flow_rate_unit || (activeFilter === 'LIVE' ? 'v/h' : 'trips');
    const formattedVal = val.toLocaleString();

    // In historical modes, normalize to hourly rate for consistent flow coloring
    const hourlyRate = activeFilter === 'LIVE' ? val : (
      activeFilter === '1hr' ? val :
      activeFilter === '6hrs' ? val / 5.8 :
      activeFilter === '12hrs' ? val / 11.5 : val / 22.8
    );

    if (hourlyRate < 200) {
      return { bg: 'bg-[#14291D]/80 hover:bg-[#14291D]', text: 'text-[#1B7A43]', label: `${formattedVal} ${unit}` };
    }
    if (hourlyRate <= 400) {
      return { bg: 'bg-[#2E2A14]/80 hover:bg-[#2E2A14]', text: 'text-[#F2D04E]', label: `${formattedVal} ${unit}` };
    }
    return { bg: 'bg-[#3A1717]/80 hover:bg-[#3A1717]', text: 'text-[#971D1B]', label: `${formattedVal} ${unit}` };
  };

  // Export Handlers
  const handleExportCSV = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${activeFilter}_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setExportToast(`${filename.replace(/_/g, ' ')} exported successfully!`);
    setTimeout(() => setExportToast(null), 3000);
  };

  const handleExportODMatrix = () => {
    let csv = 'ORIGIN/DEST,' + zones.join(',') + '\n';
    zones.forEach((origin) => {
      const row = zones.map((dest) => matrixData[origin][dest] ?? '-').join(',');
      csv += `${origin},${row}\n`;
    });
    handleExportCSV('TRACE_OD_Matrix', csv);
  };

  const handleExportSegmentDetails = () => {
    let csv = 'SEGMENT_NAME,VEHICLES_TRAVELLING,MAX_CAPACITY,TIMESTAMP,CONGESTION_INDEX\n';
    csv += `"${selectedSegment.shortName}",${selectedSegment.vehiclesTravelling},${selectedSegment.maxCapacity},"${selectedSegment.timestamp}","${selectedSegment.congestionIndex}"\n`;
    handleExportCSV('TRACE_Segment_Details', csv);
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-6 select-none relative">
      {/* Export Toast Notification */}
      {exportToast && (
        <div className="fixed top-20 right-8 z-50 bg-[#F2D04E] text-black font-heading font-bold text-sm px-4 py-2.5 rounded-xl flex items-center gap-2">
          <span>✓</span>
          <span>{exportToast}</span>
        </div>
      )}

      {/* ================= 1. TOP TABS NAVIGATION BAR (Strokes Removed) ================= */}
      <div className="bg-[#151515] rounded-[3px] p-4 md:px-8 flex items-center justify-around">
        <button
          onClick={() => setActiveTab('HEATMAP')}
          className={`relative py-2 px-6 font-heading text-lg md:text-xl font-bold tracking-widest transition-all cursor-pointer ${
            activeTab === 'HEATMAP' ? 'text-white' : 'text-[#A0A0A0] hover:text-white'
          }`}
        >
          HEATMAP
          {activeTab === 'HEATMAP' && (
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-[3px]" />
          )}
        </button>

        <button
          onClick={() => setActiveTab('OD_MATRIX')}
          className={`relative py-2 px-6 font-heading text-lg md:text-xl font-bold tracking-widest transition-all cursor-pointer ${
            activeTab === 'OD_MATRIX' ? 'text-white' : 'text-[#A0A0A0] hover:text-white'
          }`}
        >
          OD MATRIX
          {activeTab === 'OD_MATRIX' && (
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-[3px]" />
          )}
        </button>

        <button
          onClick={() => setActiveTab('SEGMENT_DETAIL')}
          className={`relative py-2 px-6 font-heading text-lg md:text-xl font-bold tracking-widest transition-all cursor-pointer ${
            activeTab === 'SEGMENT_DETAIL' ? 'text-white' : 'text-[#A0A0A0] hover:text-white'
          }`}
        >
          SEGMENT DETAIL
          {activeTab === 'SEGMENT_DETAIL' && (
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-[3px]" />
          )}
        </button>
      </div>

      {/* ================= 2. HEATMAP SECTION (Google Maps-Style Traffic Vector Flow) ================= */}
      {activeTab === 'HEATMAP' && (
        <div className="bg-[#151515] rounded-[3px] p-6 flex flex-col gap-6">
          {/* Header Metadata Section */}
          <div className="space-y-4">
            {/* Location Title & Filter Row */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Location Title */}
              <div className="flex items-center gap-3">
                <img src="/assets/heatmap_location.svg" alt="Location Pin" className="w-6 h-7 object-contain" />
                <h1 className="text-2xl md:text-3xl font-bold font-heading text-white tracking-wide">
                  {heatmapData?.corridor_name || 'University Ave Corridor (S05)'}
                </h1>
              </div>

              {/* Time Filter Controls Bar (Filter Slide Yellow Background Perfectly Fitted) */}
              <div className="bg-[#000000] p-1 rounded-[3px] flex items-center gap-1 self-start md:self-auto h-9">
                {(['LIVE', '1hr', '6hrs', '12hrs', '24hrs'] as TimeFilter[]).map((filter) => {
                  const isActive = activeFilter === filter;
                  const label = filter === 'LIVE' ? 'LIVE' : `Past ${filter}`;
                  return (
                    <button
                      key={filter}
                      onClick={() => setActiveFilter(filter)}
                      className={`h-full px-3.5 flex items-center justify-center rounded-[3px] text-xs font-body font-bold transition-all cursor-pointer select-none leading-none ${
                        isActive ? 'bg-[#F2D04E] text-black' : 'text-[#A0A0A0] hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Corridor Subtitle */}
            <p className="text-xs md:text-sm font-body text-[#A0A0A0] max-w-4xl leading-relaxed">
              {heatmapData?.subtitle || 'Flow velocity is optimal across cameras 020, 023, 028 with moderate traffic near Cam 029. University Ave corridor monitored across 4 synchronized cameras.'}
            </p>

            {/* Info Metrics Grid Row */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
              <div className="text-xs md:text-sm font-body text-[#AEA793] space-y-2">
                <div className="flex items-center gap-2">
                  <img src="/assets/heatmap_camera.svg" alt="Cameras" className="w-4 h-4 object-contain" />
                  <span>{heatmapData?.cameras_label || 'Camera 020, Camera 023, Camera 028, Camera 029'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <img src="/assets/heatmap_vehicles.svg" alt="Vehicles" className="w-4 h-4 object-contain" />
                  <span className="text-[#AEA793] font-semibold font-body">
                    {heatmapData ? `${heatmapData.total_vehicles.toLocaleString()} vehicles` : '78 vehicles'}
                  </span>
                </div>
              </div>

              <div className="text-xs md:text-sm font-body text-[#AEA793] flex items-center gap-2">
                <span>Maximum Capacity:</span>
                <span className="text-[#AEA793] font-bold font-body text-sm md:text-base">
                  {heatmapData ? `${heatmapData.max_capacity.toLocaleString()} vehicles` : '480 vehicles'}
                </span>
              </div>
            </div>
          </div>

          {/* Interactive Google Maps-Style Traffic Corridor (Dual-Layer Vector Routes) */}
          <div className="relative rounded-[3px] overflow-hidden bg-[#000000] h-[520px] w-full">
            <Map center={[-90.6847, 42.4991]} zoom={14.8}>
              {/* 1. Google Maps Vector Traffic Routes on University Ave */}
              {roadSegments.map((seg, idx) => {
                const segColor = seg.color || (
                  seg.avg_speed_kmph < 35.0 ? '#971D1B' :
                  seg.avg_speed_kmph < 50.0 ? '#F2D04E' : '#1B7A43'
                );
                return (
                  <React.Fragment key={seg.name || idx}>
                    {/* Dark casing/halo under traffic line for crisp contrast */}
                    <MapRoute
                      coordinates={seg.coordinates}
                      color="#000000"
                      width={9}
                      opacity={0.75}
                    />
                    {/* Vibrant vector traffic flow line */}
                    <MapRoute
                      coordinates={seg.coordinates}
                      color={segColor}
                      width={5.5}
                      opacity={0.96}
                    />
                  </React.Fragment>
                );
              })}

              {/* 2. S05 Corridor Camera Markers with Dynamic Velocity Tooltips */}
              {monitoredSegments.map((cam) => {
                const stat = heatmapData?.camera_stats?.find(
                  (s) => s.camera_id === cam.title || s.name === cam.title || (cam.shortName && s.short_name?.includes(cam.shortName.slice(0, 7)))
                );
                const speed = stat?.avg_speed_kmph || (cam.statusColor === 'red' ? 31.0 : cam.statusColor === 'yellow' ? 44.0 : 55.0);
                const vCount = stat?.vehicle_count || cam.vehiclesTravelling;

                return (
                  <MapMarker key={cam.id} longitude={cam.lng} latitude={cam.lat}>
                    <MarkerContent>
                      <div className="relative group cursor-pointer">
                        {/* Circular status indicator */}
                        <div
                          className={`w-5 h-5 rounded-full flex items-center justify-center border-2 border-white/90 shadow-lg ${
                            cam.statusColor === 'red'
                              ? 'bg-[#971D1B] shadow-[0_0_12px_#971D1B]'
                              : cam.statusColor === 'yellow'
                              ? 'bg-[#F2D04E] shadow-[0_0_8px_#F2D04E]'
                              : 'bg-[#1B7A43] shadow-[0_0_8px_#1B7A43]'
                          }`}
                        >
                          <div className="w-1.5 h-1.5 rounded-full bg-white/90" />
                        </div>

                        {/* Camera short label badge */}
                        <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 px-1.5 py-0.5 bg-black/90 border border-white/20 rounded text-[9px] font-bold text-white whitespace-nowrap pointer-events-none shadow">
                          {cam.shortName.split(' ')[0]}
                        </div>
                      </div>
                    </MarkerContent>
                    <MarkerTooltip>{cam.title} • {speed} km/h</MarkerTooltip>
                    <MarkerPopup>
                      <div className="bg-[#161616] p-3.5 rounded-lg text-left space-y-1.5 font-body text-xs min-w-[210px] border border-white/10 shadow-2xl">
                        <p className="font-bold text-white text-sm font-heading">{cam.title}</p>
                        <div className="text-[#A0A0A0] space-y-1 pt-1">
                          <div className="flex justify-between">
                            <span>Traffic Velocity:</span>
                            <strong className="text-[#F2D04E] font-mono">{speed} km/h</strong>
                          </div>
                          <div className="flex justify-between">
                            <span>Vehicles in Feed:</span>
                            <strong className="text-white font-mono">{vCount}</strong>
                          </div>
                          <div className="flex justify-between items-center pt-0.5">
                            <span>Flow Status:</span>
                            <span
                              className={`font-bold px-1.5 py-0.5 rounded text-[10px] uppercase ${
                                cam.congestionColor === 'red'
                                   ? 'bg-[#971D1B]/30 text-[#FF6B6B] border border-[#971D1B]'
                                   : cam.congestionColor === 'yellow'
                                   ? 'bg-[#F2D04E]/20 text-[#F2D04E] border border-[#F2D04E]/50'
                                   : 'bg-[#1B7A43]/20 text-[#4ADE80] border border-[#1B7A43]'
                              }`}
                            >
                              {cam.congestionIndex}
                            </span>
                          </div>
                        </div>
                      </div>
                    </MarkerPopup>
                  </MapMarker>
                );
              })}
            </Map>

            {/* Google Maps-Style Traffic Legend & Live Velocity Badge */}
            <div className="absolute bottom-4 left-4 z-10 bg-[#121212]/95 backdrop-blur-md px-4 py-3 rounded-[4px] border border-white/10 shadow-2xl font-body text-xs min-w-[240px] space-y-2 select-none pointer-events-auto">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
                  <span className="font-bold text-white uppercase tracking-wider text-[11px] font-heading">
                    TRAFFIC FLOW
                  </span>
                </div>
                <span className="text-[10px] text-[#F2D04E] font-mono font-bold">
                  Avg {heatmapData?.avg_corridor_speed || 52} km/h
                </span>
              </div>

              {/* Segmented Google Maps Bar */}
              <div className="space-y-1">
                <div className="h-2 w-full rounded-full flex overflow-hidden border border-white/5">
                  <div className="h-full w-1/3 bg-[#1B7A43]" title="Fast (> 50 km/h)" />
                  <div className="h-full w-1/3 bg-[#F2D04E]" title="Moderate (35 - 50 km/h)" />
                  <div className="h-full w-1/3 bg-[#971D1B]" title="Slow (< 35 km/h)" />
                </div>
                <div className="flex justify-between text-[10px] text-[#A0A0A0] font-medium pt-0.5">
                  <span className="text-[#1B7A43] font-semibold">Fast (&gt;50)</span>
                  <span className="text-[#F2D04E] font-semibold">Moderate</span>
                  <span className="text-[#971D1B] font-semibold">Slow (&lt;35)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= 3. OD MATRIX SECTION (Strokes Removed) ================= */}
      {activeTab === 'OD_MATRIX' && (
        <div className="bg-[#151515] rounded-[3px] p-6 md:p-8 flex flex-col gap-6">
          {/* Header Row: Location Title, Filter Slide & Description */}
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Location Title */}
              <div className="flex items-center gap-3">
                <img src="/assets/heatmap_location.svg" alt="Location Pin" className="w-6 h-7 object-contain" />
                <h1 className="text-2xl md:text-3xl font-bold font-heading text-white tracking-wide">
                  {odMatrixData?.corridor_name || heatmapData?.corridor_name || 'University Ave Corridor (S05)'}
                </h1>
              </div>

              {/* Time Filter Controls Bar (Filter Slide Yellow Background Perfectly Fitted) */}
              <div className="bg-[#000000] p-1 rounded-[3px] flex items-center gap-1 self-start md:self-auto h-9">
                {(['LIVE', '1hr', '6hrs', '12hrs', '24hrs'] as TimeFilter[]).map((filter) => {
                  const isActive = activeFilter === filter;
                  const label = filter === 'LIVE' ? 'LIVE' : `Past ${filter}`;
                  return (
                    <button
                      key={filter}
                      onClick={() => setActiveFilter(filter)}
                      className={`h-full px-3.5 flex items-center justify-center rounded-[3px] text-xs font-body font-bold transition-all cursor-pointer select-none leading-none ${
                        isActive ? 'bg-[#F2D04E] text-black' : 'text-[#A0A0A0] hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Subtitle Description */}
            <p className="text-sm md:text-base text-[#AEA793] font-body max-w-4xl leading-relaxed">
              {odMatrixData?.subtitle || 'Dynamic cross-camera vehicle flow and hourly throughput computed in real-time across 4 synchronized corridor cameras.'}
            </p>
          </div>

          {/* Flow Category Legend Row */}
          <div className="flex flex-wrap items-center gap-6 text-xs md:text-sm font-body font-medium text-[#AEA793] pt-2">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#1B7A43]" />
              <span>{activeFilter === 'LIVE' ? 'Normal Flow ( < 200 v/h )' : 'Normal Flow'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#F2D04E]" />
              <span>{activeFilter === 'LIVE' ? 'Moderate Flow ( 200 - 400 v/h )' : 'Moderate Flow'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#971D1B]" />
              <span>{activeFilter === 'LIVE' ? 'Heavy Flow ( > 400 v/h )' : 'Heavy Flow'}</span>
            </div>
          </div>

          {/* OD Matrix Data Table (Strokes/Borders Removed) */}
          <div className="w-full overflow-x-auto rounded-[3px] bg-[#000000]">
            <table className="w-full border-collapse text-center select-none">
              <thead>
                <tr className="bg-[#111111]">
                  <th className="py-4 px-6 text-xs font-body font-bold tracking-wider text-[#A0A0A0] text-left uppercase">
                    ORIGIN / DEST
                  </th>
                  {zones.map((zone) => (
                    <th
                      key={zone}
                      className="py-4 px-4 text-xs font-body font-bold tracking-wider text-white uppercase"
                    >
                      {zone}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {zones.map((originZone) => (
                  <tr key={originZone} className="transition-colors hover:bg-white/[0.02]">
                    <td className="py-4 px-6 text-xs font-body font-bold text-white text-left tracking-wider bg-[#111111]">
                      {originZone}
                    </td>

                    {zones.map((destZone) => {
                      const val = matrixData[originZone]?.[destZone] ?? null;
                      const style = getCellStyling(val);
                      return (
                        <td
                          key={`${originZone}-${destZone}`}
                          className={`py-4 px-4 text-xs font-body font-semibold tracking-wide transition-all ${style.bg} ${style.text}`}
                        >
                          {style.label}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bottom Export Button Row */}
          <div className="flex justify-end pt-2">
            <button
              onClick={handleExportODMatrix}
              className="cursor-pointer focus:outline-none"
              title="Export OD Matrix Data (CSV)"
            >
              <img 
                src="/assets/od_matrix_export_btn.svg" 
                alt="Export Button" 
                className="h-10 md:h-11 w-auto object-contain" 
              />
            </button>
          </div>
        </div>
      )}

      {/* ================= 4. SEGMENT DETAIL SECTION (Strokes & Hovering Side Arrow Removed, Hanken Grotesk Font) ================= */}
      {activeTab === 'SEGMENT_DETAIL' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT COLUMN: MONITORED SEGMENTS LIST (4/12 Width) */}
          <div className="lg:col-span-4 bg-[#151515] rounded-[3px] p-5 flex flex-col gap-4">
            <h2 className="text-lg md:text-xl font-bold font-heading text-white uppercase tracking-wider mb-1">
              MONITORED SEGMENTS
            </h2>

            {/* List of 4 Monitored Segment Cards (Yellow strokes removed, Hanken Grotesk font) */}
            <div className="space-y-3.5">
              {monitoredSegments.map((seg) => {
                const isSelected = seg.id === selectedSegmentId;
                
                let titleColorClass = 'text-[#1B7A43]';
                if (seg.statusColor === 'red') titleColorClass = 'text-[#971D1B]';
                if (seg.statusColor === 'yellow') titleColorClass = 'text-[#F2D04E]';

                return (
                  <div
                    key={seg.id}
                    onClick={() => setSelectedSegmentId(seg.id)}
                    className="bg-[#000000] rounded-[3px] p-4 cursor-pointer flex items-center justify-between"
                  >
                    <div className="space-y-1.5">
                      {/* Segment title font set to Hanken Grotesk (font-body) */}
                      <h3 className={`text-sm md:text-base font-bold font-body ${titleColorClass}`}>
                        {seg.title}
                      </h3>
                      <div className="text-xs font-body text-white/90 space-y-0.5">
                        <p>
                          <span className="text-[#A0A0A0]">Vehicles Travelling : </span>
                          <span className="font-semibold text-[#AEA793]">{seg.vehiclesTravelling}</span>
                        </p>
                        <p>
                          <span className="text-[#A0A0A0]">Maximum Capacity : </span>
                          <span className="font-semibold text-[#AEA793]">{seg.maxCapacity}</span>
                        </p>
                      </div>
                    </div>

                    {/* Right Side Arrow Icon (Hovering interactive removed) */}
                    <div className="pl-2">
                      <img 
                        src="/assets/segment_side_arrow.svg" 
                        alt="Select Segment" 
                        className="w-3 h-4 object-contain"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RIGHT COLUMN: SELECTED SEGMENT GRAPH & DETAILS (8/12 Width) */}
          <div className="lg:col-span-8 bg-[#151515] rounded-[3px] p-6 flex flex-col justify-between min-h-[500px] gap-6">
            <div className="space-y-6">
              {/* Header Row: Location Title & Time Filter Slide */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                {/* Location Title */}
                <div className="flex items-center gap-3">
                  <img 
                    src="/assets/segment_location.svg" 
                    alt="Segment Location" 
                    className="w-5 h-6 object-contain"
                  />
                  <h1 className="text-2xl md:text-3xl font-bold font-heading text-white tracking-wide">
                    {selectedSegment.shortName}
                  </h1>
                </div>

                {/* Time Filter Controls Bar (Filter Slide Yellow Background Perfectly Fitted) */}
                <div className="bg-[#000000] p-1 rounded-[3px] flex items-center gap-1 self-start md:self-auto h-9">
                  {(['LIVE', '1hr', '6hrs', '12hrs', '24hrs'] as TimeFilter[]).map((filter) => {
                    const isActive = activeFilter === filter;
                    const label = filter === 'LIVE' ? 'LIVE' : `Past ${filter}`;
                    return (
                      <button
                        key={filter}
                        onClick={() => setActiveFilter(filter)}
                        className={`h-full px-3.5 flex items-center justify-center rounded-[3px] text-xs font-body font-bold transition-all cursor-pointer select-none leading-none ${
                          isActive ? 'bg-[#F2D04E] text-black' : 'text-[#A0A0A0] hover:text-white hover:bg-white/5'
                        }`}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Key Metadata Stats Block */}
              <div className="space-y-1.5 text-xs md:text-sm font-body text-white/90">
                <p>
                  <span className="text-[#A0A0A0]">Vehicles Travelling : </span>
                  <span className="font-semibold text-[#AEA793]">{selectedSegment.vehiclesTravelling}</span>
                </p>
                <p>
                  <span className="text-[#A0A0A0]">Maximum Capacity : </span>
                  <span className="font-semibold text-[#AEA793]">{selectedSegment.maxCapacity}</span>
                </p>
                <p>
                  <span className="text-[#A0A0A0]">Timestamp : </span>
                  <span className="font-semibold text-[#AEA793]">{selectedSegment.timestamp}</span>
                </p>
                <p>
                  <span className="text-[#A0A0A0]">Traffic Congestion Index : </span>
                  {/* Font set to Hanken Grotesk (font-body) */}
                  <span className={`font-bold font-body ${
                    selectedSegment.congestionColor === 'red'
                      ? 'text-[#971D1B]'
                      : selectedSegment.congestionColor === 'yellow'
                      ? 'text-[#F2D04E]'
                      : 'text-[#1B7A43]'
                  }`}>
                    {selectedSegment.congestionIndex}
                  </span>
                </p>
              </div>

              {/* Main Segment Speed Live Dynamic Interactive Graph (Strokes Removed) */}
              <div className="w-full bg-[#000000] rounded-[3px] p-3 flex items-center justify-center overflow-hidden">
                <SegmentSpeedChart filter={activeFilter} segmentName={selectedSegment.shortName} />
              </div>
            </div>

            {/* Bottom Export Action Button Row */}
            <div className="flex justify-end pt-2">
              <button
                onClick={handleExportSegmentDetails}
                className="cursor-pointer focus:outline-none"
                title="Export Segment Details (CSV)"
              >
                <img 
                  src="/assets/segment_export_btn.svg" 
                  alt="Export Button" 
                  className="h-10 md:h-11 w-auto object-contain" 
                />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
