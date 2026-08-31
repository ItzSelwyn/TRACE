import React from 'react';
import { CameraFeedItem } from '../../types/dashboard';

interface CameraGridProps {
  cameras: CameraFeedItem[];
  onSelectCamera?: (cameraId: string) => void;
}

export const CameraGrid: React.FC<CameraGridProps> = ({ cameras, onSelectCamera }) => {
  return (
    <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col h-full select-none">
      {/* Panel Header */}
      <div className="flex items-center gap-2.5 mb-3.5">
        <img src="/assets/camera.svg" alt="Cameras Icon" className="w-5 h-5 brightness-0 invert" />
        <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
          CAMERAS
        </h2>
      </div>

      {/* 2x2 Camera Video Grid with Minimal Gap */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-0.5 flex-1">
        {cameras.slice(0, 4).map((cam, index) => (
          <div
            key={cam.id}
            className="relative bg-[#111111] rounded-lg overflow-hidden aspect-video flex flex-col justify-between border border-white/5 shadow-inner cursor-default"
          >
            {/* Grid Crosshair & Scanline Placeholder Background */}
            <div className="absolute inset-0 bg-[radial-gradient(#222_1px,transparent_1px)] [background-size:16px_16px] opacity-40 pointer-events-none" />

            {/* Centered Camera Footage Icon Placeholder */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-[#1A1A1A] border border-[#F2D04E]/30 flex items-center justify-center shadow-lg">
                <img 
                  src="/assets/camera.svg" 
                  alt="Camera Footage Icon" 
                  className="w-5 h-5 md:w-6 md:h-6 object-contain"
                />
              </div>
              <span className="mt-2 text-[10px] font-mono tracking-widest text-[#F2D04E]/80 uppercase">
                CAM 0{index + 1} • LIVE FOOTAGE
              </span>
            </div>

            {/* Top-Left Live Timestamp Overlay */}
            <div className="relative z-10 p-2 text-[10px] font-mono text-white/90 tracking-tight drop-shadow-md flex items-center justify-between pointer-events-none">
              <div className="bg-black/60 px-2 py-0.5 rounded backdrop-blur-xs">
                <span>{cam.timestamp}</span>
              </div>
            </div>

            {/* Bottom Camera Label Overlay */}
            <div className="relative z-10 p-2 text-[11px] font-heading font-semibold text-white/90 bg-gradient-to-t from-black/80 to-transparent flex items-center justify-between pointer-events-none">
              <span className="truncate">{cam.name} — {cam.location}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
