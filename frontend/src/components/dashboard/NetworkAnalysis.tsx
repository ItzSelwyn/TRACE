import React from 'react';
import { NetworkAnalysisStats } from '../../types/dashboard';

interface NetworkAnalysisProps {
  stats: NetworkAnalysisStats;
  onNavigateCameras?: () => void;
}

export const NetworkAnalysis: React.FC<NetworkAnalysisProps> = ({ 
  stats, 
  onNavigateCameras 
}) => {
  return (
    <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col justify-between h-full select-none">
      {/* Header */}
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2.5">
          <img src="/assets/Analystics.svg" alt="Network Analysis Icon" className="w-5 h-5 brightness-0 invert" />
          <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
            NETWORK ANALYSIS
          </h2>
        </div>
        <button
          onClick={onNavigateCameras}
          className="text-[#A0A0A0] hover:text-[#F2D04E] transition-colors p-1"
          title="View Camera Network"
        >
          <span className="text-sm font-bold">↗</span>
        </button>
      </div>

      {/* 3 Metric Boxes */}
      <div className="grid grid-cols-3 gap-3 flex-1">
        {/* Uptime */}
        <div className="bg-[#151515] rounded-lg p-3 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] font-bold text-[#A0A0A0] font-heading tracking-wider uppercase mb-1">
            UPTIME
          </span>
          <span className="text-2xl sm:text-3xl font-semibold text-[#F2D04E] font-body">
            {stats.uptimeFormatted}
          </span>
        </div>

        {/* Cameras Active (#1B7A43) */}
        <div className="bg-[#151515] rounded-lg p-3 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] font-bold text-[#A0A0A0] font-heading tracking-wider uppercase mb-1">
            CAMERAS ACTIVE
          </span>
          <span className="text-2xl sm:text-3xl font-semibold text-[#1B7A43] font-body">
            {stats.camerasActive}
          </span>
        </div>

        {/* Cameras Down (#AC251D) */}
        <div className="bg-[#151515] rounded-lg p-3 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] font-bold text-[#A0A0A0] font-heading tracking-wider uppercase mb-1">
            CAMERAS DOWN
          </span>
          <span className="text-2xl sm:text-3xl font-semibold text-[#AC251D] font-body">
            {stats.camerasDown}
          </span>
        </div>
      </div>
    </div>
  );
};
