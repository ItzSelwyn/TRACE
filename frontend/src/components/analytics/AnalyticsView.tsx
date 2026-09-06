import React, { useState } from 'react';
import {
  Map,
  MapMarker,
  MarkerContent,
  MarkerTooltip,
  MarkerPopup,
  MapHeatmap,
  HeatmapPoint,
} from '@/components/ui/map';

export type AnalyticsTab = 'HEATMAP' | 'OD_MATRIX' | 'SEGMENT_DETAIL';
export type TimeFilter = 'LIVE' | '1hr' | '6hrs' | '12hrs' | '24hrs';

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
const SegmentSpeedChart: React.FC<{ filter: TimeFilter; segmentName: string }> = ({ filter }) => {
  const [hoveredPoint, setHoveredPoint] = useState<{ time: string; speed: number; x: number; y: number } | null>(null);

  // Dynamic sample data based on time filter
  const getFilterData = () => {
    switch (filter) {
      case 'LIVE':
        return [
          { time: '10:00', speed: 75 },
          { time: '10:05', speed: 68 },
          { time: '10:10', speed: 52 },
          { time: '10:15', speed: 38 },
          { time: '10:20', speed: 28 },
          { time: '10:23', speed: 32 },
        ];
      case '1hr':
        return [
          { time: '09:30', speed: 80 },
          { time: '09:40', speed: 72 },
          { time: '09:50', speed: 55 },
          { time: '10:00', speed: 42 },
          { time: '10:10', speed: 30 },
          { time: '10:23', speed: 32 },
        ];
      case '6hrs':
        return [
          { time: '05:00', speed: 88 },
          { time: '06:00', speed: 70 },
          { time: '07:00', speed: 45 },
          { time: '08:00', speed: 25 },
          { time: '09:00', speed: 35 },
          { time: '10:00', speed: 32 },
        ];
      case '12hrs':
        return [
          { time: '22:00', speed: 92 },
          { time: '01:00', speed: 95 },
          { time: '04:00', speed: 88 },
          { time: '07:00', speed: 42 },
          { time: '09:00', speed: 28 },
          { time: '10:23', speed: 32 },
        ];
      default: // 24hrs
        return [
          { time: '00:00', speed: 85 },
          { time: '04:00', speed: 90 },
          { time: '08:00', speed: 38 },
          { time: '12:00', speed: 45 },
          { time: '16:00', speed: 28 },
          { time: '20:00', speed: 65 },
          { time: '24:00', speed: 82 },
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

  // Heatmap Point Data for Maplibre/mapcn
  const heatmapPoints: HeatmapPoint[] = [
    { lng: -73.985, lat: 40.748, weight: 1.0 },
    { lng: -73.986, lat: 40.749, weight: 0.9 },
    { lng: -73.984, lat: 40.747, weight: 0.8 },
    { lng: -73.982, lat: 40.750, weight: 0.7 },
    { lng: -73.987, lat: 40.752, weight: 0.95 },
    { lng: -73.990, lat: 40.755, weight: 0.6 },
    { lng: -73.978, lat: 40.744, weight: 0.85 },
    { lng: -73.975, lat: 40.742, weight: 0.9 },
    { lng: -73.981, lat: 40.746, weight: 1.0 },
  ];

  // OD Matrix Zones & Data Structure
  const zones = ['Z-NORTH', 'Z-CENTRAL', 'Z-EAST', 'Z-SOUTH', 'Z-PORT', 'Z-INDUS'];

  const matrixData: Record<string, Record<string, number | null>> = {
    'Z-NORTH': { 'Z-NORTH': null, 'Z-CENTRAL': 342, 'Z-EAST': 118, 'Z-SOUTH': 210, 'Z-PORT': 85, 'Z-INDUS': 64 },
    'Z-CENTRAL': { 'Z-NORTH': 280, 'Z-CENTRAL': null, 'Z-EAST': 390, 'Z-SOUTH': 450, 'Z-PORT': 312, 'Z-INDUS': 145 },
    'Z-EAST': { 'Z-NORTH': 120, 'Z-CENTRAL': 295, 'Z-EAST': null, 'Z-SOUTH': 178, 'Z-PORT': 90, 'Z-INDUS': 112 },
    'Z-SOUTH': { 'Z-NORTH': 190, 'Z-CENTRAL': 410, 'Z-EAST': 142, 'Z-SOUTH': null, 'Z-PORT': 310, 'Z-INDUS': 230 },
    'Z-PORT': { 'Z-NORTH': 95, 'Z-CENTRAL': 510, 'Z-EAST': 125, 'Z-SOUTH': 305, 'Z-PORT': null, 'Z-INDUS': 490 },
    'Z-INDUS': { 'Z-NORTH': 78, 'Z-CENTRAL': 165, 'Z-EAST': 88, 'Z-SOUTH': 240, 'Z-PORT': 490, 'Z-INDUS': null },
  };

  // Monitored Segments List
  const monitoredSegments: MonitoredSegment[] = [
    {
      id: 1,
      title: 'Segment 1 - North Highway 16',
      shortName: 'North Highway 16 (Segment 1)',
      statusColor: 'red',
      vehiclesTravelling: 452,
      maxCapacity: 480,
      timestamp: '10:23:01 am',
      congestionIndex: 'Critical',
      congestionColor: 'red',
      lng: -73.985,
      lat: 40.748,
    },
    {
      id: 2,
      title: 'Segment 2 - North Highway 16',
      shortName: 'North Highway 16 (Segment 2)',
      statusColor: 'yellow',
      vehiclesTravelling: 93,
      maxCapacity: 170,
      timestamp: '10:23:01 am',
      congestionIndex: 'Moderate',
      congestionColor: 'yellow',
      lng: -73.987,
      lat: 40.752,
    },
    {
      id: 3,
      title: 'Segment 3 - North Highway 16',
      shortName: 'North Highway 16 (Segment 3)',
      statusColor: 'green',
      vehiclesTravelling: 70,
      maxCapacity: 200,
      timestamp: '10:23:01 am',
      congestionIndex: 'Optimal',
      congestionColor: 'green',
      lng: -73.981,
      lat: 40.744,
    },
    {
      id: 4,
      title: 'Segment 4 - North Highway 16',
      shortName: 'North Highway 16 (Segment 4)',
      statusColor: 'green',
      vehiclesTravelling: 53,
      maxCapacity: 300,
      timestamp: '10:23:01 am',
      congestionIndex: 'Optimal',
      congestionColor: 'green',
      lng: -73.978,
      lat: 40.741,
    },
  ];

  const selectedSegment = monitoredSegments.find((s) => s.id === selectedSegmentId) || monitoredSegments[0];

  // Helper to determine flow type styling for OD matrix
  const getCellStyling = (val: number | null) => {
    if (val === null) {
      return { bg: 'bg-[#151515]', text: 'text-[#666666]', label: '-' };
    }
    if (val < 200) {
      return { bg: 'bg-[#14291D]/80 hover:bg-[#14291D]', text: 'text-[#1B7A43]', label: `${val} v/h` };
    }
    if (val <= 400) {
      return { bg: 'bg-[#2E2A14]/80 hover:bg-[#2E2A14]', text: 'text-[#F2D04E]', label: `${val} v/h` };
    }
    return { bg: 'bg-[#3A1717]/80 hover:bg-[#3A1717]', text: 'text-[#971D1B]', label: `${val} v/h` };
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
      <div className="bg-[#1E1E1E] rounded-xl p-4 md:px-8 flex items-center justify-around">
        <button
          onClick={() => setActiveTab('HEATMAP')}
          className={`relative py-2 px-6 font-heading text-lg md:text-xl font-bold tracking-widest transition-all cursor-pointer ${
            activeTab === 'HEATMAP' ? 'text-white' : 'text-[#A0A0A0] hover:text-white'
          }`}
        >
          HEATMAP
          {activeTab === 'HEATMAP' && (
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-full" />
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
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-full" />
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
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-full" />
          )}
        </button>
      </div>

      {/* ================= 2. HEATMAP SECTION (Strokes Removed) ================= */}
      {activeTab === 'HEATMAP' && (
        <div className="bg-[#1E1E1E] rounded-xl p-6 flex flex-col gap-6">
          {/* Header Metadata Section */}
          <div className="space-y-4">
            {/* Location Title & Filter Row */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Location Title */}
              <div className="flex items-center gap-3">
                <img src="/assets/heatmap_location.svg" alt="Location Pin" className="w-6 h-7 object-contain" />
                <h1 className="text-2xl md:text-3xl font-bold font-heading text-white tracking-wide">
                  North Highway 16
                </h1>
              </div>

              {/* Time Filter Controls Bar (Filter Slide Yellow Background Perfectly Fitted) */}
              <div className="bg-[#151515] p-1 rounded-[3px] flex items-center gap-1 self-start md:self-auto h-9">
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
            <p className="text-sm md:text-base text-[#AEA793] font-body leading-relaxed max-w-4xl">
              Flow velocity is 85% below optimal. Queue propagation originating from intersection node CAM-W-402.
            </p>

            {/* Info Metrics Grid Row */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
              <div className="text-xs md:text-sm font-body text-[#AEA793] space-y-2">
                <div className="flex items-center gap-2">
                  <img src="/assets/heatmap_camera.svg" alt="Cameras" className="w-4 h-4 object-contain" />
                  <span>Camera 16, Camera 15, Camera 14</span>
                </div>
                <div className="flex items-center gap-2">
                  <img src="/assets/heatmap_vehicles.svg" alt="Vehicles" className="w-4 h-4 object-contain" />
                  <span className="text-[#AEA793] font-semibold font-body">452 vehicles</span>
                </div>
              </div>

              <div className="text-xs md:text-sm font-body text-[#AEA793] flex items-center gap-2">
                <span>Maximum Capacity:</span>
                <span className="text-[#AEA793] font-bold font-body text-sm md:text-base">
                  480 vehicles
                </span>
              </div>
            </div>
          </div>

          {/* Interactive Heatmap Map (MapCN Map - Stroke Removed) */}
          <div className="relative rounded-xl overflow-hidden bg-[#151515] h-[520px] w-full">
            <Map center={[-73.983, 40.747]} zoom={13.2}>
              <MapHeatmap data={heatmapPoints} radius={40} opacity={0.85} intensity={1.3} />

              {monitoredSegments.map((seg) => (
                <MapMarker key={seg.id} longitude={seg.lng} latitude={seg.lat}>
                  <MarkerContent>
                    <div className="w-4 h-4 rounded-full bg-[#971D1B] border-2 border-white animate-pulse" />
                  </MarkerContent>
                  <MarkerTooltip>{seg.title}</MarkerTooltip>
                  <MarkerPopup>
                    <div className="bg-[#161616] p-3 rounded-lg text-left space-y-1 font-body text-xs min-w-[160px]">
                      <p className="font-bold text-white font-body">{seg.title}</p>
                      <p className="text-[#A0A0A0]">Vehicles: <strong className="text-white">{seg.vehiclesTravelling}</strong></p>
                      <p className="text-[#A0A0A0]">Congestion: <strong className="text-[#971D1B]">{seg.congestionIndex}</strong></p>
                    </div>
                  </MarkerPopup>
                </MapMarker>
              ))}
            </Map>

            <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
              <img
                src="/assets/traffic_congestion_index.svg"
                alt="Traffic Congestion Index"
                className="w-auto h-20 md:h-24 object-contain"
              />
            </div>
          </div>
        </div>
      )}

      {/* ================= 3. OD MATRIX SECTION (Strokes Removed) ================= */}
      {activeTab === 'OD_MATRIX' && (
        <div className="bg-[#1E1E1E] rounded-xl p-6 md:p-8 flex flex-col gap-6">
          {/* Header Row: Description & Filter Slide */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <p className="text-sm md:text-base text-[#AEA793] font-body max-w-2xl leading-relaxed">
              Cross-sector vehicle velocity, journey counts, and throughput volume computed via multi-camera plate re-identification.
            </p>

            {/* Time Filter Controls Bar (Filter Slide Yellow Background Perfectly Fitted) */}
            <div className="bg-[#151515] p-1 rounded-[3px] flex items-center gap-1 self-start md:self-auto h-9">
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

          {/* Flow Category Legend Row */}
          <div className="flex flex-wrap items-center gap-6 text-xs md:text-sm font-body font-medium text-[#AEA793] pt-2">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#1B7A43]" />
              <span>Normal Flow ( &lt; 200 v/h )</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#F2D04E]" />
              <span>Moderate Flow ( 200 - 400 v/h )</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#971D1B]" />
              <span>Heavy Flow ( &gt; 400 v/h )</span>
            </div>
          </div>

          {/* OD Matrix Data Table (Strokes/Borders Removed) */}
          <div className="w-full overflow-x-auto rounded-xl bg-[#151515]">
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
                      const val = matrixData[originZone][destZone];
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
          <div className="lg:col-span-4 bg-[#1E1E1E] rounded-xl p-5 flex flex-col gap-4">
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
                    className="bg-[#111111] rounded-xl p-4 cursor-pointer flex items-center justify-between"
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
          <div className="lg:col-span-8 bg-[#1E1E1E] rounded-xl p-6 flex flex-col justify-between min-h-[500px] gap-6">
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
                <div className="bg-[#151515] p-1 rounded-[3px] flex items-center gap-1 self-start md:self-auto h-9">
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
              <div className="w-full bg-[#111111] rounded-xl p-3 flex items-center justify-center overflow-hidden">
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
