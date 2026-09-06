import React, { useState } from 'react';

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
}

export const AnalyticsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AnalyticsTab>('HEATMAP');
  const [activeFilter, setActiveFilter] = useState<TimeFilter>('LIVE');
  const [selectedSegmentId, setSelectedSegmentId] = useState<number>(1);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [exportToast, setExportToast] = useState<string | null>(null);

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.15, 2.2));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 0.15, 0.8));
  };

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

  // Monitored Segments List (Matching Design Screenshot Exactly)
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
    },
  ];

  const selectedSegment = monitoredSegments.find((s) => s.id === selectedSegmentId) || monitoredSegments[0];

  // Helper to determine flow type styling for OD matrix
  const getCellStyling = (val: number | null) => {
    if (val === null) {
      return { bg: 'bg-[#151515]', text: 'text-[#666666]', label: '-' };
    }
    if (val < 200) {
      return { bg: 'bg-[#14291D]/80 hover:bg-[#14291D]', text: 'text-[#26D07C]', label: `${val} v/h` };
    }
    if (val <= 400) {
      return { bg: 'bg-[#2E2A14]/80 hover:bg-[#2E2A14]', text: 'text-[#F2D04E]', label: `${val} v/h` };
    }
    return { bg: 'bg-[#3A1717]/80 hover:bg-[#3A1717]', text: 'text-[#FF4D4D]', label: `${val} v/h` };
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
        <div className="fixed top-20 right-8 z-50 bg-[#F2D04E] text-black font-heading font-bold text-sm px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 animate-bounce">
          <span>✓</span>
          <span>{exportToast}</span>
        </div>
      )}

      {/* ================= 1. TOP TABS NAVIGATION BAR ================= */}
      <div className="bg-[#1E1E1E] rounded-xl p-4 md:px-8 flex items-center justify-around border border-white/5 shadow-xl">
        <button
          onClick={() => setActiveTab('HEATMAP')}
          className={`relative py-2 px-6 font-heading text-lg md:text-xl font-bold tracking-widest transition-all cursor-pointer ${
            activeTab === 'HEATMAP' ? 'text-white' : 'text-[#A0A0A0] hover:text-white'
          }`}
        >
          HEATMAP
          {activeTab === 'HEATMAP' && (
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-full shadow-md" />
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
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-full shadow-md" />
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
            <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#F2D04E] rounded-full shadow-md" />
          )}
        </button>
      </div>

      {/* ================= 2. HEATMAP SECTION ================= */}
      {activeTab === 'HEATMAP' && (
        <div className="bg-[#1E1E1E] rounded-xl p-6 border border-white/5 shadow-2xl flex flex-col gap-6">
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

              {/* Time Filter Controls Bar */}
              <div className="bg-[#151515] p-1 rounded-lg border border-white/10 flex items-center gap-1 self-start md:self-auto shadow-inner">
                {(['LIVE', '1hr', '6hrs', '12hrs', '24hrs'] as TimeFilter[]).map((filter) => {
                  const isActive = activeFilter === filter;
                  const label = filter === 'LIVE' ? 'LIVE' : `Past ${filter}`;
                  return (
                    <button
                      key={filter}
                      onClick={() => setActiveFilter(filter)}
                      className={`px-3 py-1.5 rounded text-xs font-heading font-bold transition-all cursor-pointer ${
                        isActive ? 'bg-[#F2D04E] text-black shadow-md' : 'text-[#A0A0A0] hover:text-white hover:bg-white/5'
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
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-white/5">
              <div className="space-y-2 text-xs md:text-sm font-body text-[#AEA793]">
                <div className="flex items-center gap-2">
                  <img src="/assets/heatmap_camera.svg" alt="Cameras" className="w-4 h-4 object-contain" />
                  <span>Camera 16, Camera 15, Camera 14</span>
                </div>
                <div className="flex items-center gap-2">
                  <img src="/assets/heatmap_vehicles.svg" alt="Vehicles" className="w-4 h-4 object-contain" />
                  <span className="text-white font-semibold">452 vehicles</span>
                </div>
              </div>

              <div className="text-xs md:text-sm font-body text-[#AEA793] flex items-center gap-2">
                <span>Maximum Capacity:</span>
                <span className="text-white font-bold font-heading text-sm md:text-base">
                  480 vehicles
                </span>
              </div>
            </div>
          </div>

          {/* Heatmap Map Graphic & Interactive Controls Overlay */}
          <div className="relative rounded-xl overflow-hidden bg-[#151515] border border-white/10 shadow-2xl min-h-[520px] flex items-center justify-center">
            <div className="w-full h-full overflow-hidden flex items-center justify-center">
              <img
                src="/assets/heatmap.svg"
                alt="City Traffic Heatmap"
                className="w-full h-full object-cover transition-transform duration-300 ease-out transform-gpu"
                style={{ transform: `scale(${zoomLevel})` }}
              />
            </div>

            <div className="absolute bottom-4 left-4 z-10">
              <img
                src="/assets/traffic_congestion_index.svg"
                alt="Traffic Congestion Index"
                className="w-auto h-20 md:h-24 drop-shadow-2xl object-contain"
              />
            </div>

            <div className="absolute bottom-4 right-4 z-10 flex items-center gap-2">
              <button
                onClick={handleZoomIn}
                className="cursor-pointer focus:outline-none transition-transform hover:scale-110 active:scale-95 shadow-xl"
                title="Zoom In"
              >
                <img src="/assets/zoom_in.svg" alt="Zoom In" className="w-9 h-9 object-contain" />
              </button>
              <button
                onClick={handleZoomOut}
                className="cursor-pointer focus:outline-none transition-transform hover:scale-110 active:scale-95 shadow-xl"
                title="Zoom Out"
              >
                <img src="/assets/zoom_out.svg" alt="Zoom Out" className="w-9 h-9 object-contain" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= 3. OD MATRIX SECTION ================= */}
      {activeTab === 'OD_MATRIX' && (
        <div className="bg-[#1E1E1E] rounded-xl p-6 md:p-8 border border-white/5 shadow-2xl flex flex-col gap-6">
          {/* Header Row: Description & Filter Slide */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <p className="text-sm md:text-base text-[#AEA793] font-body max-w-2xl leading-relaxed">
              Cross-sector vehicle velocity, journey counts, and throughput volume computed via multi-camera plate re-identification.
            </p>

            {/* Time Filter Controls Bar */}
            <div className="bg-[#151515] p-1 rounded-lg border border-white/10 flex items-center gap-1 self-start md:self-auto shadow-inner">
              {(['LIVE', '1hr', '6hrs', '12hrs', '24hrs'] as TimeFilter[]).map((filter) => {
                const isActive = activeFilter === filter;
                const label = filter === 'LIVE' ? 'LIVE' : `Past ${filter}`;
                return (
                  <button
                    key={filter}
                    onClick={() => setActiveFilter(filter)}
                    className={`px-3 py-1.5 rounded text-xs font-heading font-bold transition-all cursor-pointer ${
                      isActive ? 'bg-[#F2D04E] text-black shadow-md' : 'text-[#A0A0A0] hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Flow Category Legend Row */}
          <div className="flex flex-wrap items-center gap-6 text-xs md:text-sm font-heading font-medium text-[#AEA793] pt-2">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#26D07C]" />
              <span>Normal Flow ( &lt; 200 v/h )</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#F2D04E]" />
              <span>Moderate Flow ( 200 - 400 v/h )</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-[#FF4D4D]" />
              <span>Heavy Flow ( &gt; 400 v/h )</span>
            </div>
          </div>

          {/* OD Matrix Data Table */}
          <div className="w-full overflow-x-auto rounded-xl border border-white/10 bg-[#151515] shadow-2xl">
            <table className="w-full border-collapse text-center select-none">
              <thead>
                <tr className="border-b border-white/10 bg-[#111111]">
                  <th className="py-4 px-6 text-xs font-heading font-bold tracking-wider text-[#A0A0A0] text-left uppercase border-r border-white/10">
                    ORIGIN / DEST
                  </th>
                  {zones.map((zone) => (
                    <th
                      key={zone}
                      className="py-4 px-4 text-xs font-heading font-bold tracking-wider text-white uppercase border-r border-white/5 last:border-r-0"
                    >
                      {zone}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {zones.map((originZone) => (
                  <tr key={originZone} className="transition-colors hover:bg-white/[0.02]">
                    <td className="py-4 px-6 text-xs font-heading font-bold text-white text-left tracking-wider bg-[#111111] border-r border-white/10">
                      {originZone}
                    </td>

                    {zones.map((destZone) => {
                      const val = matrixData[originZone][destZone];
                      const style = getCellStyling(val);
                      return (
                        <td
                          key={`${originZone}-${destZone}`}
                          className={`py-4 px-4 text-xs font-heading font-semibold tracking-wide border-r border-white/5 last:border-r-0 transition-all ${style.bg} ${style.text}`}
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
              className="cursor-pointer focus:outline-none transition-transform hover:scale-105 active:scale-95 duration-200"
              title="Export OD Matrix Data (CSV)"
            >
              <img 
                src="/assets/od_matrix_export_btn.svg" 
                alt="Export Button" 
                className="h-10 md:h-11 w-auto object-contain drop-shadow-xl" 
              />
            </button>
          </div>
        </div>
      )}

      {/* ================= 4. SEGMENT DETAIL SECTION (Matching UI Screenshot Exactly) ================= */}
      {activeTab === 'SEGMENT_DETAIL' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT COLUMN: MONITORED SEGMENTS LIST (4/12 Width) */}
          <div className="lg:col-span-4 bg-[#1E1E1E] rounded-xl p-5 border border-white/5 shadow-2xl flex flex-col gap-4">
            <h2 className="text-lg md:text-xl font-bold font-heading text-white uppercase tracking-wider mb-1">
              MONITORED SEGMENTS
            </h2>

            {/* List of 4 Monitored Segment Cards */}
            <div className="space-y-3.5">
              {monitoredSegments.map((seg) => {
                const isSelected = seg.id === selectedSegmentId;
                
                // Color mapping for segment titles based on status
                let titleColorClass = 'text-[#26D07C]';
                if (seg.statusColor === 'red') titleColorClass = 'text-[#FF4D4D]';
                if (seg.statusColor === 'yellow') titleColorClass = 'text-[#F2D04E]';

                return (
                  <div
                    key={seg.id}
                    onClick={() => setSelectedSegmentId(seg.id)}
                    className={`bg-[#111111] rounded-xl p-4 cursor-pointer transition-all border ${
                      isSelected
                        ? 'border-[#F2D04E] shadow-lg shadow-black/80 ring-1 ring-[#F2D04E]/50'
                        : 'border-white/5 hover:border-white/20'
                    } flex items-center justify-between group`}
                  >
                    <div className="space-y-1.5">
                      <h3 className={`text-sm md:text-base font-bold font-heading ${titleColorClass}`}>
                        {seg.title}
                      </h3>
                      <div className="text-xs font-body text-white/90 space-y-0.5">
                        <p>
                          <span className="text-[#A0A0A0]">Vehicles Travelling : </span>
                          <span className="font-semibold text-white">{seg.vehiclesTravelling}</span>
                        </p>
                        <p>
                          <span className="text-[#A0A0A0]">Maximum Capacity : </span>
                          <span className="font-semibold text-white">{seg.maxCapacity}</span>
                        </p>
                      </div>
                    </div>

                    {/* Right Side Arrow Icon */}
                    <div className="pl-2">
                      <img 
                        src="/assets/segment_side_arrow.svg" 
                        alt="Select Segment" 
                        className="w-3 h-4 object-contain transition-transform group-hover:translate-x-1"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RIGHT COLUMN: SELECTED SEGMENT GRAPH & DETAILS (8/12 Width) */}
          <div className="lg:col-span-8 bg-[#1E1E1E] rounded-xl p-6 border border-white/5 shadow-2xl flex flex-col justify-between min-h-[500px] gap-6">
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

                {/* Time Filter Controls Bar */}
                <div className="bg-[#151515] p-1 rounded-lg border border-white/10 flex items-center gap-1 self-start md:self-auto shadow-inner">
                  {(['LIVE', '1hr', '6hrs', '12hrs', '24hrs'] as TimeFilter[]).map((filter) => {
                    const isActive = activeFilter === filter;
                    const label = filter === 'LIVE' ? 'LIVE' : `Past ${filter}`;
                    return (
                      <button
                        key={filter}
                        onClick={() => setActiveFilter(filter)}
                        className={`px-3 py-1.5 rounded text-xs font-heading font-bold transition-all cursor-pointer ${
                          isActive ? 'bg-[#F2D04E] text-black shadow-md' : 'text-[#A0A0A0] hover:text-white hover:bg-white/5'
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
                  <span className="font-semibold text-white">{selectedSegment.vehiclesTravelling}</span>
                </p>
                <p>
                  <span className="text-[#A0A0A0]">Maximum Capacity : </span>
                  <span className="font-semibold text-white">{selectedSegment.maxCapacity}</span>
                </p>
                <p>
                  <span className="text-[#A0A0A0]">Timestamp : </span>
                  <span className="font-semibold text-white">{selectedSegment.timestamp}</span>
                </p>
                <p>
                  <span className="text-[#A0A0A0]">Traffic Congestion Index : </span>
                  <span className={`font-bold font-heading ${
                    selectedSegment.congestionColor === 'red'
                      ? 'text-[#FF4D4D]'
                      : selectedSegment.congestionColor === 'yellow'
                      ? 'text-[#F2D04E]'
                      : 'text-[#26D07C]'
                  }`}>
                    {selectedSegment.congestionIndex}
                  </span>
                </p>
              </div>

              {/* Main Segment Speed & Velocity Timeline Graph */}
              <div className="w-full bg-[#111111] rounded-xl p-3 border border-white/10 shadow-2xl flex items-center justify-center overflow-hidden">
                <img 
                  src="/assets/segment_details_graph.svg" 
                  alt="Segment Speed Timeline Graph" 
                  className="w-full h-auto max-h-[350px] object-contain"
                />
              </div>
            </div>

            {/* Bottom Export Action Button Row */}
            <div className="flex justify-end pt-2">
              <button
                onClick={handleExportSegmentDetails}
                className="cursor-pointer focus:outline-none transition-transform hover:scale-105 active:scale-95 duration-200"
                title="Export Segment Details (CSV)"
              >
                <img 
                  src="/assets/segment_export_btn.svg" 
                  alt="Export Button" 
                  className="h-10 md:h-11 w-auto object-contain drop-shadow-xl" 
                />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
