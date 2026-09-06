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
    <div className="bg-[#151515] rounded-[3px] p-4 flex flex-col justify-between select-none">
      {/* Header */}
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2.5">
          <img src="/assets/Analystics.svg" alt="Network Analysis Icon" className="w-5 h-5 brightness-0 invert" />
          <h2 className="text-sm md:text-base font-bold tracking-wider text-white font-heading uppercase">
            NETWORK ANALYSIS
          </h2>
        </div>
        <button
          onClick={onNavigateCameras}
          className="text-white p-1 cursor-pointer"
          title="View Camera Network"
        >
          <img src="/assets/diagonal_arrow.svg" alt="Arrow" className="w-4 h-4 object-contain brightness-0 invert" />
        </button>
      </div>

      {/* 3 Metric Boxes */}
      <div className="grid grid-cols-3 gap-3 flex-1">
        {/* Uptime */}
        <div className="bg-[#000000] rounded-[3px] p-3.5 sm:p-4 flex flex-col items-center justify-start text-center">
          <span className="text-xs md:text-sm font-bold text-[#A0A0A0] font-heading tracking-wider uppercase text-center mb-2">
            UPTIME
          </span>
          <span className="text-2xl sm:text-3xl lg:text-4xl font-semibold text-[#F2D04E] font-body text-center mt-1">
            {stats.uptimeFormatted}
          </span>
        </div>

        {/* Cameras Active (#1B7A43) */}
        <div className="bg-[#000000] rounded-[3px] p-3.5 sm:p-4 flex flex-col items-center justify-start text-center">
          <span className="text-xs md:text-sm font-bold text-[#A0A0A0] font-heading tracking-wider uppercase text-center mb-2">
            CAMERAS ACTIVE
          </span>
          <span className="text-2xl sm:text-3xl lg:text-4xl font-semibold text-[#1B7A43] font-body text-center mt-1">
            {stats.camerasActive}
          </span>
        </div>

        {/* Cameras Down (#AC251D) */}
        <div className="bg-[#000000] rounded-[3px] p-3.5 sm:p-4 flex flex-col items-center justify-start text-center">
          <span className="text-xs md:text-sm font-bold text-[#A0A0A0] font-heading tracking-wider uppercase text-center mb-2">
            CAMERAS DOWN
          </span>
          <span className="text-2xl sm:text-3xl lg:text-4xl font-semibold text-[#AC251D] font-body text-center mt-1">
            {stats.camerasDown}
          </span>
        </div>
      </div>
    </div>
  );
};
