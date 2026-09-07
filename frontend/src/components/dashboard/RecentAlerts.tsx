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
                  <svg width="16" height="16" viewBox="0 0 20 19" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 object-contain">
                    <path d="M16.3235 12.8229L14.3235 11.6647L18 8.90284L20 10.061L16.3235 12.8229ZM10.5294 9.88286L14.3529 7.03189L5.08824 1.74573L2.88235 5.51732L10.5294 9.88286ZM0 19V17.2181H6.17647V9.43739L2 7.06159C1.56726 6.80501 1.28755 6.43893 1.16088 5.96338C1.03402 5.48782 1.09804 5.03226 1.35294 4.5967L3.55882 0.884505C3.81373 0.468739 4.17157 0.196512 4.63235 0.0678227C5.09314 -0.0608666 5.52941 -0.00642109 5.94118 0.231159L17.5588 6.85371L10.6471 11.9914L7.94118 10.4471V17.2181C7.94118 17.7082 7.76843 18.1276 7.42294 18.4764C7.07726 18.8255 6.66176 19 6.17647 19H0Z" fill="#A0A0A0"/>
                  </svg>
                  <span>{alert.cameraName} ({alert.location})</span>
                </div>
                <div className="flex items-center gap-2">
                  <svg width="12" height="15" viewBox="0 0 12 15" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 object-contain opacity-80">
                    <path d="M6.92813 6.92813C7.18438 6.67188 7.3125 6.3625 7.3125 6C7.3125 5.6375 7.18438 5.32812 6.92813 5.07188C6.67188 4.81563 6.3625 4.6875 6 4.6875C5.6375 4.6875 5.32812 4.81563 5.07188 5.07188C4.81563 5.32812 4.6875 5.6375 4.6875 6C4.6875 6.3625 4.81563 6.67188 5.07188 6.92813C5.32812 7.18438 5.6375 7.3125 6 7.3125C6.3625 7.3125 6.67188 7.18438 6.92813 6.92813ZM6 13.5187C7.6625 12.0062 8.89062 10.6344 9.68438 9.40313C10.4781 8.17188 10.875 7.0875 10.875 6.15C10.875 4.675 10.4031 3.46875 9.45938 2.53125C8.51562 1.59375 7.3625 1.125 6 1.125C4.6375 1.125 3.48438 1.59375 2.54063 2.53125C1.59688 3.46875 1.125 4.675 1.125 6.15C1.125 7.0875 1.53125 8.17188 2.34375 9.40313C3.15625 10.6344 4.375 12.0062 6 13.5187ZM6 15C3.9875 13.2875 2.48438 11.6969 1.49063 10.2281C0.496875 8.75937 0 7.4 0 6.15C0 4.275 0.603125 2.78125 1.80938 1.66875C3.01563 0.55625 4.4125 0 6 0C7.5875 0 8.98438 0.55625 10.1906 1.66875C11.3969 2.78125 12 4.275 12 6.15C12 7.4 11.5031 8.75937 10.5094 10.2281C9.51562 11.6969 8.0125 13.2875 6 15Z" fill="#A0A0A0"/>
                  </svg>
                  <span className="font-semibold text-[#A0A0A0]">North Highway 06</span>
                </div>
              </div>

              {/* View Action Button */}
              <div className="flex justify-end pt-1">
                <button
                  onClick={() => onViewAlertTrace && onViewAlertTrace(alert.plateNumber)}
                  className="bg-[#1E1E1E] hover:bg-[#2A2A2A] text-[#A0A0A0] hover:text-white font-bold font-body text-xs md:text-sm px-4 py-1.5 rounded-[3px] flex items-center gap-1.5 cursor-pointer transition-all"
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
