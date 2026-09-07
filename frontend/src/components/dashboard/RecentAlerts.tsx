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
    <div className="bg-[#151515] rounded-[3px] p-4 flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3.5 select-none">
        <div className="flex items-center gap-2.5">
          <img src="/assets/Alerts.svg" alt="Recent Alerts Icon" className="w-5 h-5 brightness-0 invert" />
          <h2 className="text-sm md:text-base font-bold tracking-wider text-white font-heading uppercase">
            RECENT ALERTS
          </h2>
        </div>
        <button
          onClick={onNavigateAlerts}
          className="text-white p-1 cursor-pointer"
          title="View All Alerts"
        >
          <img src="/assets/diagonal_arrow.svg" alt="Arrow" className="w-4 h-4 object-contain brightness-0 invert" />
        </button>
      </div>

      {/* Alert Cards Container */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 flex-1">
        {alerts.map((alert) => {
          const isBlacklist = alert.alertType === 'BLACKLIST';
          return (
            <div
              key={alert.id}
              className="bg-[#000000] rounded-[3px] p-4 flex flex-col justify-between transition-all"
            >
              {/* Card Header: Plate Number, Tag & Confidence */}
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base md:text-lg text-white font-heading tracking-wide">
                    {alert.plateNumber}
                  </span>
                  <span
                    className={`text-xs md:text-sm font-bold font-heading ${
                      isBlacklist ? 'text-[#AC251D]' : 'text-[#F2D04E]'
                    }`}
                  >
                    ({alert.alertType})
                  </span>
                </div>
                <span className="text-sm md:text-base font-bold text-[#1B7A43] font-heading">
                  {alert.confidence}%
                </span>
              </div>

              {/* Subtitle: Camera & Location Stacked Lines */}
              <div className="space-y-1.5 text-xs md:text-sm text-[#A0A0A0] font-body mb-3">
                <div className="flex items-center gap-2">
                  <img src="/assets/camera_aea793.svg" alt="Camera" className="w-4 h-4 object-contain" />
                  <span>{alert.cameraName} ({alert.location})</span>
                </div>
                <div className="flex items-center gap-2">
                  <img src="/assets/alert_location.svg" alt="Location" className="w-4 h-4 object-contain opacity-80" />
                  <span className="font-semibold text-[#AEA793]">North Highway 06</span>
                </div>
              </div>

              {/* View Action Button */}
              <div className="flex justify-end pt-1">
                <button
                  onClick={() => onViewAlertTrace && onViewAlertTrace(alert.plateNumber)}
                  className="bg-[#1E1E1E] hover:bg-[#2A2A2A] text-[#AEA793] hover:text-white font-bold font-body text-xs md:text-sm px-4 py-1.5 rounded-[3px] flex items-center gap-1.5 cursor-pointer transition-all"
                >
                  <span>VIEW</span>
                  <img src="/assets/diagonal_arrow.svg" alt="Arrow" className="w-3.5 h-3.5 object-contain" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
