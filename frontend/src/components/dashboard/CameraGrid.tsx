import React, { useEffect, useState } from 'react';
import { CameraFeedItem } from '../../types/dashboard';

interface CameraGridProps {
  cameras: CameraFeedItem[];
  selectedCameraId?: string;
  onSelectCamera?: (cameraId: string) => void;
  activeCameraCount?: number;
}

export const CameraGrid: React.FC<CameraGridProps> = ({
  cameras,
  selectedCameraId = 'c020',
  onSelectCamera,
  activeCameraCount,
}) => {
  const [feedErrors, setFeedErrors] = useState<Record<string, boolean>>({});
  const [activeMode, setActiveMode] = useState<number>(activeCameraCount ?? 2);
  const [switchingMode, setSwitchingMode] = useState<boolean>(false);

  // Sync mode with parent prop if updated externally
  useEffect(() => {
    if (activeCameraCount) {
      setActiveMode(activeCameraCount);
    }
  }, [activeCameraCount]);

  // Initial load: fetch current active camera count from backend
  useEffect(() => {
    fetch('/perception/cameras/mode')
      .then((res) => res.json())
      .then((data) => {
        if (data?.active_camera_count) {
          setActiveMode(data.active_camera_count);
        }
      })
      .catch(() => {});
  }, []);

  const handleFeedError = (cameraId: string) => {
    setFeedErrors((prev) => ({ ...prev, [cameraId]: true }));
  };

  const handleModeChange = async (count: number) => {
    try {
      setSwitchingMode(true);
      setActiveMode(count);
      await fetch('/perception/cameras/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count, primary_camera_id: selectedCameraId }),
      });
      // Clear errors so streams re-render seamlessly
      setFeedErrors({});
    } catch (err) {
      console.warn('Failed to switch camera mode:', err);
    } finally {
      setSwitchingMode(false);
    }
  };

  const handleCameraClick = async (camId: string) => {
    onSelectCamera?.(camId.toLowerCase());

    // In 2-camera mode, if user selects a camera that is currently in standby,
    // dynamically activate the pair that includes this selected camera
    const targetCam = cameras.find((c) => c.id.toLowerCase() === camId.toLowerCase());
    if (activeMode === 2 && targetCam && targetCam.enabled === false) {
      try {
        await fetch('/perception/cameras/mode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ count: 2, primary_camera_id: camId.toLowerCase() }),
        });
        setFeedErrors({});
      } catch (err) {
        console.warn('Failed to switch active camera pair:', err);
      }
    }
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

        {/* 2-CAM / 4-CAM Processing Load Toggle */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-[#888] uppercase tracking-wider hidden xs:inline">
            AI Load:
          </span>
          <div className="flex items-center bg-[#000000] border border-[#2b2b2b] rounded-[3px] p-0.5 text-[11px] font-mono">
            <button
              type="button"
              onClick={() => handleModeChange(2)}
              disabled={switchingMode}
              className={`px-2 py-0.5 rounded-[2px] transition-all duration-150 ${
                activeMode === 2
                  ? 'bg-[#1B7A43] text-white font-bold shadow-sm'
                  : 'text-[#888] hover:text-white hover:bg-[#1a1a1a]'
              }`}
              title="Run models on 2 cameras only (reduces CPU/GPU load)"
            >
              2 CAMS
            </button>
            <button
              type="button"
              onClick={() => handleModeChange(4)}
              disabled={switchingMode}
              className={`px-2 py-0.5 rounded-[2px] transition-all duration-150 ${
                activeMode === 4
                  ? 'bg-[#1B7A43] text-white font-bold shadow-sm'
                  : 'text-[#888] hover:text-white hover:bg-[#1a1a1a]'
              }`}
              title="Run models on all 4 cameras"
            >
              4 CAMS
            </button>
          </div>
        </div>
      </div>

      {/* Camera Video Feeds — 2x2 Grid Layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {cameras.map((cam, index) => {
          const isSelected = cam.id.toLowerCase() === selectedCameraId.toLowerCase();
          const hasError = feedErrors[cam.id];
          const isStandby = cam.enabled === false;

          return (
            <div
              key={cam.id}
              onClick={() => handleCameraClick(cam.id)}
              className={`relative bg-[#000000] rounded-[3px] overflow-hidden aspect-video flex flex-col justify-between transition-all duration-200 cursor-pointer ${
                isSelected ? 'ring-2 ring-[#1B7A43]' : ''
              }`}
            >
              {/* Standby / Disabled Badge Overlay */}
              {isStandby && (
                <div className="absolute top-2 right-2 bg-black/80 backdrop-blur-sm border border-white/15 px-2 py-0.5 rounded-[2px] text-[9px] font-mono text-white/90 z-10 tracking-widest uppercase">
                  STANDBY
                </div>
              )}

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

            </div>
          );
        })}
      </div>
    </div>
  );
};
