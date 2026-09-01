import React, { useState } from 'react';
import { CameraFeedItem } from '../../types/dashboard';

interface CameraGridProps {
  cameras: CameraFeedItem[];
  selectedCameraId?: string;
  onSelectCamera?: (cameraId: string) => void;
}

export const CameraGrid: React.FC<CameraGridProps> = ({
  cameras,
  selectedCameraId = 'c020',
  onSelectCamera,
}) => {
  const [feedErrors, setFeedErrors] = useState<Record<string, boolean>>({});

  const handleFeedError = (cameraId: string) => {
    setFeedErrors((prev) => ({ ...prev, [cameraId]: true }));
  };

  return (
    <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col h-full select-none">
      {/* Panel Header */}
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2.5">
          <img src="/assets/camera.svg" alt="Cameras Icon" className="w-5 h-5 brightness-0 invert" />
          <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
            CAMERAS
          </h2>
        </div>
      </div>

      {/* 2x2 Camera Video Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 flex-1">
        {cameras.slice(0, 4).map((cam, index) => {
          const isSelected = cam.id.toLowerCase() === selectedCameraId.toLowerCase();
          const hasError = feedErrors[cam.id];

          return (
            <div
              key={cam.id}
              onClick={() => onSelectCamera && onSelectCamera(cam.id.toLowerCase())}
              className={`relative bg-[#0d0d0d] rounded-lg overflow-hidden aspect-video flex flex-col justify-between transition-all duration-200 cursor-pointer shadow-md ${
                isSelected
                  ? 'border-2 border-[#1B7A43] ring-1 ring-[#1B7A43]/40'
                  : 'border border-white/10 hover:border-white/30'
              }`}
            >
              {/* Live Video Stream from Backend */}
              {!hasError ? (
                <img
                  src={`/perception/camera/${cam.id.toLowerCase()}/feed`}
                  alt={cam.name}
                  className="absolute inset-0 w-full h-full object-cover z-0"
                  onError={() => handleFeedError(cam.id)}
                />
              ) : null}

              {/* Fallback Placeholder if Video is offline */}
              {hasError && (
                <>
                  <div className="absolute inset-0 bg-[radial-gradient(#222_1px,transparent_1px)] [background-size:16px_16px] opacity-40 pointer-events-none" />
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
                </>
              )}

              {/* Top-Right Dot Overlay: Yellow when idle, Green when clicked/selected */}
              <div className="relative z-10 p-2.5 flex items-center justify-end pointer-events-none">
                <span
                  className={`w-2.5 h-2.5 rounded-full shadow-md transition-colors duration-200 ${
                    isSelected ? 'bg-[#1B7A43]' : 'bg-[#F2D04E]'
                  }`}
                />
              </div>

              {/* Bottom Clean Camera Number */}
              <div className="relative z-10 p-2 text-[11px] font-heading font-semibold text-white/90 drop-shadow-md pointer-events-none">
                <span>{cam.name}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
