import React, { useState } from 'react';

export type NavRoute = 'dashboard' | 'vehicle-trace' | 'analytics' | 'alerts' | 'blacklist' | 'cameras' | 'home';

interface SidebarProps {
  currentRoute: NavRoute;
  onNavigate: (route: NavRoute) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentRoute, 
  onNavigate 
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const navItems: { id: NavRoute; label: string; icon: string; enabled: boolean; hasRedAlert?: boolean }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '/assets/Dashboard.svg', enabled: true },
    { id: 'vehicle-trace', label: 'Vehicle Trace', icon: '/assets/route.svg', enabled: true },
    { id: 'analytics', label: 'Analytics', icon: '/assets/Analystics.svg', enabled: false },
    { id: 'alerts', label: 'Alerts', icon: '/assets/Alerts.svg', enabled: false, hasRedAlert: true },
    { id: 'blacklist', label: 'Blacklist', icon: '/assets/Blacklist.svg', enabled: false },
    { id: 'cameras', label: 'Cameras', icon: '/assets/camera.svg', enabled: false },
  ];

  const handleItemClick = (item: typeof navItems[0]) => {
    if (item.enabled) {
      onNavigate(item.id);
    }
  };

  return (
    <aside 
      className={`bg-[#151515] flex flex-col justify-start transition-all duration-300 relative z-20 select-none ${
        isExpanded ? 'w-56' : 'w-16'
      }`}
    >
      {/* Menu Items Stack */}
      <div className="pt-4 flex flex-col items-stretch gap-2.5">
        {navItems.map((item) => {
          const isActive = currentRoute === item.id;
          return (
            <div key={item.id} className="relative w-full px-2">
              <button
                onClick={() => handleItemClick(item)}
                disabled={!item.enabled}
                className={`w-full h-11 flex items-center transition-all ${
                  isExpanded ? 'px-3 justify-start' : 'justify-center'
                } ${
                  isActive
                    ? 'bg-[#F2D04E] text-black font-bold rounded-lg shadow-sm'
                    : item.enabled
                    ? 'bg-transparent text-[#F2D04E] hover:bg-[#1E1E1E] rounded-lg'
                    : 'bg-transparent text-[#F2D04E]/50 cursor-not-allowed opacity-60 rounded-lg'
                }`}
                title={item.enabled ? item.label : `${item.label} (UI Pending)`}
                aria-label={item.label}
              >
                {/* Icon */}
                <img 
                  src={item.icon} 
                  alt={item.label}
                  className={`w-5 h-5 shrink-0 transition-transform ${
                    isActive ? 'brightness-0' : ''
                  }`}
                />

                {/* Red notification badge on Alerts (#AC251D) */}
                {item.hasRedAlert && !isActive && (
                  <span className="absolute top-2 right-3 w-2 h-2 rounded-full bg-[#AC251D] shadow-sm" />
                )}

                {/* Sidebar open text labels */}
                {isExpanded && (
                  <span className={`ml-3 text-sm font-heading font-medium whitespace-nowrap ${
                    isActive ? 'text-black font-bold' : item.enabled ? 'text-[#F2D04E]' : 'text-[#F2D04E]/50'
                  }`}>
                    {item.label}
                  </span>
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Much Larger Sidebar Open Toggle Button: Positioned on right border directly below last item (Cameras), borderless */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -right-6 top-[330px] w-12 h-12 rounded-full flex items-center justify-center bg-[#151515] hover:bg-[#1E1E1E] transition-all shadow-2xl shadow-black/90 border-none outline-none z-30 group"
        title={isExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
      >
        <img 
          src="/assets/sidebar_open.svg" 
          alt="Sidebar Toggle" 
          className={`w-7 h-7 transition-transform duration-300 group-hover:scale-110 ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>
    </aside>
  );
};
