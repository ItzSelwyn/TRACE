import React from 'react';
import { DashboardAlertItem } from '../../types/dashboard';

interface RecentAlertsProps {
  alerts: DashboardAlertItem[];
  onViewAlertTrace?: (plateNumber: string) => void;
  onNavigateAlerts?: () => void;
}

export const RecentAlerts: React.FC<RecentAlertsProps> = ({ 
  alerts, 
  onViewAlertTrace,
  onNavigateAlerts 
}) => {
  return (
    <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3.5 select-none">
        <div className="flex items-center gap-2.5">
          <img src="/assets/Alerts.svg" alt="Recent Alerts Icon" className="w-5 h-5 brightness-0 invert" />
          <h2 className="text-sm font-bold tracking-wider text-white font-heading uppercase">
            RECENT ALERTS
          </h2>
        </div>
        <button
          onClick={onNavigateAlerts}
          className="text-[#A0A0A0] hover:text-[#F2D04E] transition-colors p-1"
          title="View All Alerts"
        >
          <span className="text-sm font-bold">↗</span>
        </button>
      </div>

      {/* Alert Cards Container */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1">
        {alerts.map((alert) => {
          const isBlacklist = alert.alertType === 'BLACKLIST';
          return (
            <div
              key={alert.id}
              className="bg-[#151515] rounded-lg p-3.5 flex flex-col justify-between transition-all"
            >
              {/* Card Header: Plate Number, Tag & Confidence */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-white font-heading tracking-wide">
                    {alert.plateNumber}
                  </span>
                  <span
                    className={`text-[11px] font-bold font-heading ${
                      isBlacklist ? 'text-[#AC251D]' : 'text-[#F2D04E]'
                    }`}
                  >
                    ({alert.alertType})
                  </span>
                </div>
                <span className="text-xs font-bold text-[#1B7A43] font-heading">
                  {alert.confidence}%
                </span>
              </div>

              {/* Subtitle: Camera & Location */}
              <div className="flex items-center justify-between text-xs text-[#A0A0A0] font-body mb-3">
                <div className="flex items-center gap-1.5 truncate">
                  <img src="/assets/camera.svg" alt="Camera" className="w-3.5 h-3.5 opacity-80" />
                  <span className="truncate">
                    {alert.cameraName} ({alert.location})
                  </span>
                </div>
              </div>

              {/* View Action Button */}
              <div className="flex justify-end pt-1">
                <button
                  onClick={() => onViewAlertTrace && onViewAlertTrace(alert.plateNumber)}
                  className="bg-[#1E1E1E] hover:bg-[#F2D04E] hover:text-black text-white font-bold font-heading text-[11px] px-3 py-1 rounded flex items-center gap-1 transition-all group"
                >
                  <span>VIEW</span>
                  <span className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5">↗</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
