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
    <div className="bg-[#151515] rounded-[3px] p-3.5 flex flex-col select-none">
      {/* Panel Header */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <img src="/assets/camera.svg" alt="Cameras Icon" className="w-4 h-4 brightness-0 invert" />
          <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
            CAMERAS
          </h2>
        </div>
      </div>

      {/* Camera Video Feeds — 2x2 Grid Layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {cameras.map((cam, index) => {
          const isSelected = cam.id.toLowerCase() === selectedCameraId.toLowerCase();
          const hasError = feedErrors[cam.id];

          return (
            <div
              key={cam.id}
              onClick={() => onSelectCamera && onSelectCamera(cam.id.toLowerCase())}
              className={`relative bg-[#000000] rounded-[3px] overflow-hidden aspect-video flex flex-col justify-between transition-all duration-200 cursor-pointer ${
                isSelected ? 'ring-2 ring-[#1B7A43]' : ''
              }`}
            >
              {/* Live Video Stream from Backend - strictly uncropped 16:9 */}
              {!hasError ? (
                <img
                  src={`/perception/camera/${cam.id.toLowerCase()}/feed`}
                  alt={cam.name}
                  className="absolute inset-0 w-full h-full object-contain bg-black z-0"
                  onError={() => handleFeedError(cam.id)}
                />
              ) : null}

              {/* Fallback Placeholder if Video is offline */}
              {hasError && (
                <>
                  <div className="absolute inset-0 bg-[#0A0A0A] pointer-events-none" />
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <div className="w-9 h-9 rounded-full bg-[#1A1A1A] flex items-center justify-center">
                      <img 
                        src="/assets/camera.svg" 
                        alt="Camera Footage Icon" 
                        className="w-4 h-4 object-contain"
                      />
                    </div>
                    <span className="mt-1.5 text-[9px] font-mono tracking-widest text-[#F2D04E]/80 uppercase">
                      CAM 0{index + 1} • LIVE FOOTAGE
                    </span>
                  </div>
                </>
              )}

              {/* Bottom Clean Camera Number */}
              <div className="relative z-10 p-2 text-[11px] font-heading font-semibold text-white/90 pointer-events-none">
                <span>{cam.name}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
