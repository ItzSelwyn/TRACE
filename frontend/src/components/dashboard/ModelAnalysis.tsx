import React, { useEffect, useState } from 'react';
import { ModelAnalysisData, RecentDetectionItem } from '../../types/dashboard';

interface ModelAnalysisProps {
  data: ModelAnalysisData;
  selectedCameraId?: string;
  onViewTrace?: (plateNumber: string) => void;
}

export const ModelAnalysis: React.FC<ModelAnalysisProps> = ({
  data,
  selectedCameraId = 'c020',
  onViewTrace,
}) => {
  const [liveVehicle, setLiveVehicle] = useState<any>(null);
  const activeCamId = (selectedCameraId || data.cameraId || 'c020').toLowerCase();
  const cameraDisplayName = `Camera ${activeCamId.replace('c', '').toUpperCase()}`;
  const [frameUrl, setFrameUrl] = useState<string>(
    `/perception/camera/${activeCamId}/frame?annotate=true&t=${Date.now()}`
  );

  // Smooth 10 FPS frame refresher that completely avoids browser HTTP connection pool exhaustion
  useEffect(() => {
    let isMounted = true;
    setLiveVehicle(null);
    setFrameUrl(`/perception/camera/${activeCamId}/frame?annotate=true&t=${Date.now()}`);

    const frameInterval = setInterval(() => {
      if (isMounted) {
        setFrameUrl(`/perception/camera/${activeCamId}/frame?annotate=true&t=${Date.now()}`);
      }
    }, 100); // 10 FPS

    const fetchActiveVehicle = async () => {
      try {
        const res = await fetch(`/perception/camera/${activeCamId}/active-vehicle`);
        if (!res.ok) return;
        const payload = await res.json();
        if (isMounted && payload && (payload.track_id || payload.trackId)) {
          setLiveVehicle(payload);
        }
      } catch {
        // Ignore
      }
    };

    // Fetch immediately to prevent 1-second delay / stale ID flashing
    fetchActiveVehicle();
    const vehicleInterval = setInterval(fetchActiveVehicle, 1000);

    return () => {
      isMounted = false;
      clearInterval(frameInterval);
      clearInterval(vehicleInterval);
    };
  }, [activeCamId]);

  // Real runtime perception values with clean 3-digit TRK-XXX and TRACE-CXXX-XXX formatting
  const formatTrackId = (raw: any): string => {
    if (!raw) return 'TRK-001';
    const s = String(raw);
    if (s.startsWith('TRK-')) {
      const num = s.replace(/[^0-9]/g, '');
      return `TRK-${num.padStart(3, '0')}`;
    }
    const num = s.split('-').pop()?.replace(/[^0-9]/g, '') || '1';
    return `TRK-${num.padStart(3, '0')}`;
  };

  const rawTrack = liveVehicle?.track_id || liveVehicle?.trackId || data.trackId;
  const trackId = formatTrackId(rawTrack);
  const trackNum = trackId.replace('TRK-', '');
  const observationId = liveVehicle?.observation_id || liveVehicle?.observationId || `TRACE-${activeCamId.toUpperCase()}-${trackNum}`;
  const rawPlate = liveVehicle?.plate_number || liveVehicle?.plateNumber || data.plateNumber;
  const isPlateRead = rawPlate && rawPlate !== 'NOT READ' && !rawPlate.startsWith('TRACE-');
  const displayPlate = isPlateRead ? rawPlate : 'NOT READ';
  const displayConfidence = isPlateRead ? `${liveVehicle?.ocr_confidence ?? data.ocrConfidence ?? 85}%` : 'NOT READ';
  const displayVehicleType = (liveVehicle?.vehicle_type || liveVehicle?.vehicleType || data.vehicleType || 'CAR').toUpperCase();
  const displayColor = (liveVehicle?.color || data.color || 'WHITE').toUpperCase();
  const displayTimestamp = liveVehicle?.timestamp || data.timestamp || new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
  const isMoving = liveVehicle?.is_moving ?? true;

  // Recent detections list (last 3-5 real observations dynamically streamed)
  const rawRecent = (liveVehicle?.recent_detections && liveVehicle.recent_detections.length > 0)
    ? liveVehicle.recent_detections
    : (data.recentDetections && data.recentDetections.length > 0)
      ? data.recentDetections
      : [];

  const recentDetections: RecentDetectionItem[] = rawRecent.length > 0
    ? rawRecent
    : [
        {
          id: 'rec-1',
          observationId: observationId,
          trackId: trackId,
          vehicleType: displayVehicleType,
          color: displayColor,
          plateNumber: displayPlate,
          timestamp: displayTimestamp,
          status: isMoving ? 'PASSING' : 'DETECTED',
        },
      ];

  return (
    <div className="bg-[#151515] rounded-[3px] p-3.5 flex flex-col h-full select-none">
      {/* Panel Header */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <img 
            src="/assets/model.svg" 
            alt="Model Analysis Icon" 
            className="w-4 h-4 brightness-0 invert" 
          />
          <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
            MODEL ANALYSIS - {cameraDisplayName}
          </h2>
        </div>
      </div>

      {/* Main Live Detection Frame Video - strict uncropped 16:9 */}
      <div className="relative bg-[#000000] rounded-[3px] overflow-hidden aspect-video mb-2.5 flex items-center justify-center">
        <img
          key={activeCamId}
          src={frameUrl}
          alt={`YOLOv8 Target Detection Frame - ${activeCamId}`}
          className="absolute inset-0 w-full h-full object-contain bg-black z-0"
        />
      </div>

      {/* Detail Breakdown Card */}
      <div className="bg-[#000000] rounded-[3px] p-3 flex flex-col justify-between flex-1">
        {/* Header with Camera Info & Motion Status */}
        <div className="space-y-0.5 mb-2 font-body">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#AEA793] font-body">
              <img src="/assets/camera_aea793.svg" alt="Camera" className="w-3 h-3" />
              <span>{cameraDisplayName}</span>
            </div>
            {isMoving && (
              <span className="text-[11px] font-body text-[#1B7A43] font-semibold tracking-wide">
                MOTION DETECTED
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-[#AEA793] font-body">
            <img src="/assets/route_aea793.svg" alt="Location" className="w-3.5 h-3.5" />
            <span>Live Video Feed (CityFlow)</span>
          </div>
        </div>

        {/* Track ID & Observation ID Stacked (Observation ID below Track ID, Hanken Grotesk font, no black background) */}
        <div className="space-y-1.5 mb-2 font-body">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#A0A0A0] text-xs font-body">Track ID</span>
            <span className="text-[#F2D04E] font-bold text-xs font-body">{trackId}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#A0A0A0] text-xs font-body">Observation ID</span>
            <span className="text-[#AEA793] font-body text-xs">{observationId}</span>
          </div>
        </div>

        {/* Metadata Key-Value Grid */}
        <div className="space-y-1.5 text-xs font-body pt-1.5">
          {/* Number Plate: Hanken Grotesk font, white color, no background rectangle/stroke */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Number Plate</span>
            <span className="text-white font-bold font-body text-xs">
              {displayPlate}
            </span>
          </div>

          {/* Detection / OCR Confidence */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Detection / OCR Confidence</span>
            <span className={`font-medium ${isPlateRead ? 'text-[#1B7A43] font-bold font-heading' : 'text-white'}`}>
              {displayConfidence}
            </span>
          </div>

          {/* Vehicle Type */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Vehicle Type</span>
            <span className="text-white font-medium">{displayVehicleType}</span>
          </div>

          {/* Color */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Color</span>
            <span className="text-white font-medium">{displayColor}</span>
          </div>

          {/* Timestamp */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Timestamp</span>
            <span className="text-white font-medium">{displayTimestamp}</span>
          </div>
        </div>

        {/* Compact Recent Detections List (Hanken Grotesk font for all text) */}
        <div className="mt-2 pt-2 font-body">
          <div className="flex items-center justify-between mb-1 font-body">
            <span className="text-[10px] font-body font-bold text-[#A0A0A0] uppercase tracking-wider">
              RECENT DETECTIONS ({cameraDisplayName})
            </span>
            <span className="text-[9px] font-body text-[#AEA793]">LAST {recentDetections.slice(0, 4).length}</span>
          </div>

          <div className="space-y-0.5 max-h-20 overflow-y-auto pr-0.5 font-body">
            {recentDetections.slice(0, 4).map((rec: any, idx) => {
              const recTrackId = rec.track_id || rec.trackId || `TRK-${idx + 1}`;
              const recType = (rec.vehicle_type || rec.vehicleType || 'CAR').toUpperCase();
              const recColor = (rec.color || 'WHITE').toUpperCase();
              const recPlate = rec.plate_number || rec.plateNumber || 'NOT READ';
              const recHasPlate = recPlate && recPlate !== 'NOT READ' && !recPlate.startsWith('TRACE-');
              const recTime = rec.timestamp || displayTimestamp;

              return (
                <div
                  key={rec.id || `rec-${recTrackId}-${idx}`}
                  onClick={() => onViewTrace && onViewTrace(recHasPlate ? recPlate : recTrackId)}
                  className="flex items-center justify-between bg-black/30 hover:bg-black/50 px-2 py-0.5 rounded text-[11px] font-body border border-white/5 transition-colors cursor-pointer"
                  title="Click to view vehicle trace"
                >
                  <div className="flex items-center gap-2 font-body">
                    <span className="text-[#F2D04E] font-bold font-body">{recTrackId}</span>
                    <span className="text-white/80 font-body">{recType}</span>
                    <span className="text-[#A0A0A0] text-[10px] font-body">({recColor})</span>
                  </div>

                  <div className="flex items-center gap-2 font-body">
                    {recHasPlate ? (
                      <span className="text-[#F2D04E] font-semibold font-body">{recPlate}</span>
                    ) : (
                      <span className="text-[#666666] text-[10px] font-body">NOT READ</span>
                    )}
                    <span className="text-[#888888] text-[10px] font-body">{recTime}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Action: View Reconstructed Trace (Hanken Grotesk, #AEA793 color, diagonal_arrow.svg) */}
        <div className="flex justify-end pt-2 mt-1.5">
          <button
            onClick={() => onViewTrace && onViewTrace(isPlateRead ? displayPlate : (trackId || displayPlate || 'TN 37 CY 1234'))}
            className="bg-[#1E1E1E] hover:text-white text-[#AEA793] font-bold font-body text-xs px-3 py-1 rounded flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <span>VIEW RECONSTRUCTED TRACE</span>
            <img src="/assets/diagonal_arrow.svg" alt="Arrow" className="w-3 h-3 object-contain" />
          </button>
        </div>
      </div>
    </div>
  );
};
