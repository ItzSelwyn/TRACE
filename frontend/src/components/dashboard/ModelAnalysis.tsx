import React from 'react';
import { ModelAnalysisData } from '../../types/dashboard';

interface ModelAnalysisProps {
  data: ModelAnalysisData;
  onViewTrace?: (plateNumber: string) => void;
}

export const ModelAnalysis: React.FC<ModelAnalysisProps> = ({ data, onViewTrace }) => {
  return (
    <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col h-full">
      {/* Panel Header */}
      <div className="flex items-center gap-2.5 mb-3.5 select-none">
        <img 
          src="/assets/model.svg" 
          alt="Model Analysis Icon" 
          className="w-5 h-5 brightness-0 invert" 
        />
        <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
          MODEL ANALYSIS
        </h2>
      </div>

      {/* Main Detection Frame Preview Placeholder */}
      <div className="relative bg-[#111111] rounded-lg overflow-hidden aspect-[16/9] mb-3 flex items-center justify-center border border-white/5 shadow-inner">
        {/* Grid Background Pattern */}
        <div className="absolute inset-0 bg-[radial-gradient(#222_1px,transparent_1px)] [background-size:16px_16px] opacity-40 pointer-events-none" />

        {/* Centered Camera Footage Icon Placeholder */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div className="w-14 h-14 rounded-full bg-[#1A1A1A] border border-[#F2D04E]/40 flex items-center justify-center shadow-lg">
            <img 
              src="/assets/camera.svg" 
              alt="Camera Detection Icon" 
              className="w-7 h-7 object-contain"
            />
          </div>
          <span className="mt-2 text-[10px] font-mono tracking-widest text-[#F2D04E]/80 uppercase">
            TARGET DETECTION FRAME
          </span>
        </div>

        {/* Live Timestamp Overlay */}
        <div className="absolute top-2 left-2 text-[10px] font-mono text-white bg-black/70 px-2 py-0.5 rounded backdrop-blur-sm flex items-center gap-1.5 z-10">
          <span>11-03-2026 Thur 04:31:12 pm (C13)</span>
        </div>
      </div>

      {/* Detail Breakdown Card */}
      <div className="bg-[#151515] rounded-lg p-3.5 flex flex-col justify-between flex-1">
        {/* Camera & Location Info */}
        <div className="space-y-1 mb-3">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#AEA793] font-body">
            <img src="/assets/camera.svg" alt="Camera" className="w-3.5 h-3.5 opacity-80" />
            <span>{data.cameraName}</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-[#AEA793] font-body">
            <img src="/assets/route.svg" alt="Location" className="w-3.5 h-3.5 opacity-80" />
            <span>{data.location}</span>
          </div>
        </div>

        {/* Metadata Key-Value Grid */}
        <div className="space-y-2 text-xs font-body pt-2 border-t border-white/5">
          {/* Number Plate */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Number Plate</span>
            <span className="text-[#F2D04E] font-bold font-heading text-sm tracking-wide">
              {data.plateNumber}
            </span>
          </div>

          {/* OCR Confidence (#1B7A43) */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">OCR Confidence</span>
            <span className="text-[#1B7A43] font-bold font-heading">
              {data.ocrConfidence}%
            </span>
          </div>

          {/* Vehicle Type */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Vehicle Type</span>
            <span className="text-white font-medium">{data.vehicleType}</span>
          </div>

          {/* Color */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Color</span>
            <span className="text-white font-medium">{data.color}</span>
          </div>

          {/* Timestamp */}
          <div className="flex items-center justify-between">
            <span className="text-[#A0A0A0]">Timestamp</span>
            <span className="text-white font-medium">{data.timestamp}</span>
          </div>
        </div>

        {/* Action Button: VIEW ↗ */}
        <div className="flex justify-end pt-3 mt-2 border-t border-white/5">
          <button
            onClick={() => onViewTrace && onViewTrace(data.plateNumber)}
            className="bg-[#1E1E1E] hover:bg-[#F2D04E] hover:text-black text-white font-bold font-heading text-xs px-3.5 py-1.5 rounded flex items-center gap-1.5 transition-all group"
          >
            <span>VIEW</span>
            <span className="text-sm transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5">↗</span>
          </button>
        </div>
      </div>
    </div>
  );
};
