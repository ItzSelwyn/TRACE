import React, { useEffect, useState } from 'react';
import { ModelAnalysisData } from '../../types/dashboard';

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

    const vehicleInterval = setInterval(async () => {
      try {
        const res = await fetch(`/perception/camera/${activeCamId}/active-vehicle`);
        if (!res.ok) return;
        const payload = await res.json();
        if (isMounted && payload && payload.plate_number) {
          setLiveVehicle(payload);
        }
      } catch {
        // Ignore
      }
    }, 1000);

    return () => {
      isMounted = false;
      clearInterval(frameInterval);
      clearInterval(vehicleInterval);
    };
  }, [activeCamId]);

  const displayPlate = liveVehicle?.plate_number || `TRACE-${activeCamId}-1`;
  const displayConfidence = liveVehicle?.ocr_confidence ?? 88;
  const displayVehicleType = (liveVehicle?.vehicle_type || 'CAR').toUpperCase();
  const displayColor = (liveVehicle?.color || 'WHITE').toUpperCase();
  const displayTimestamp = liveVehicle?.timestamp || new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
  const isMoving = liveVehicle?.is_moving ?? true;

  return (
    <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col h-full select-none">
      {/* Panel Header */}
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2.5">
          <img 
            src="/assets/model.svg" 
            alt="Model Analysis Icon" 
            className="w-5 h-5 brightness-0 invert" 
          />
          <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
            MODEL ANALYSIS — {cameraDisplayName}
          </h2>
        </div>
      </div>

      {/* Main Detection Frame Preview with Real-time YOLO Bounding Boxes */}
      <div className="relative bg-[#0d0d0d] rounded-lg overflow-hidden aspect-[16/9] mb-3 flex items-center justify-center border border-white/10 shadow-inner">
        {/* High-speed Real-time Frame Video */}
        <img
          key={activeCamId}
          src={frameUrl}
          alt={`YOLOv8 Target Detection Frame - ${activeCamId}`}
          className="absolute inset-0 w-full h-full object-cover z-0"
        />

        {/* Top-Right Green Indicator Dot */}
        <div className="absolute top-2.5 right-2.5 z-10 pointer-events-none">
          <span className="w-2.5 h-2.5 rounded-full bg-[#1B7A43] shadow-md inline-block" />
        </div>
      </div>

      {/* Detail Breakdown Card */}
      <div className="bg-[#151515] rounded-lg p-3.5 flex flex-col justify-between flex-1 border border-white/5">
        {/* Camera & Location Info */}
        <div className="space-y-1 mb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#AEA793] font-body">
              <img src="/assets/camera.svg" alt="Camera" className="w-3.5 h-3.5 opacity-80" />
              <span>{cameraDisplayName}</span>
            </div>
            {isMoving && (
              <span className="text-[11px] font-mono text-[#1B7A43] font-semibold tracking-wide">
                MOTION DETECTED
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-[#AEA793] font-body">
            <img src="/assets/route.svg" alt="Location" className="w-3.5 h-3.5 opacity-80" />
            <span>Live Video Feed (CityFlow)</span>
          </div>
        </div>

        {/* Metadata Key-Value Grid */}
        <div className="space-y-2 text-xs font-body pt-2 border-t border-white/5">
          {/* Number Plate */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Number Plate</span>
            <span className="text-[#F2D04E] font-bold font-heading text-sm tracking-wide">
              {displayPlate}
            </span>
          </div>

          {/* OCR Confidence */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Detection / OCR Confidence</span>
            <span className="text-[#1B7A43] font-bold font-heading">
              {displayConfidence}%
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

        {/* Action Button: VIEW ↗ */}
        <div className="flex justify-end pt-3 mt-2 border-t border-white/5">
          <button
            onClick={() => onViewTrace && onViewTrace(displayPlate)}
            className="bg-[#1E1E1E] hover:bg-[#F2D04E] hover:text-black text-white font-bold font-heading text-xs px-3.5 py-1.5 rounded flex items-center gap-1.5 transition-all group"
          >
            <span>VIEW RECONSTRUCTED TRACE</span>
            <span className="text-sm transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5">↗</span>
          </button>
        </div>
      </div>
    </div>
  );
};
