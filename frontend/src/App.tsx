import React, { useState } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar, NavRoute } from './components/layout/Sidebar';
import { DashboardView } from './components/dashboard/DashboardView';
import { VehicleTraceView } from './components/vehicle-trace/VehicleTraceView';
import { HomeView } from './components/home/HomeView';
import { mockDashboardData } from './data/mockDashboardData';
import { mockVehicleTraceData } from './data/mockVehicleTraceData';

export const App: React.FC = () => {
  // Initial starting route is 'home'
  const [currentRoute, setCurrentRoute] = useState<NavRoute | 'home'>('home');
  const [vehicleTracePayload, setVehicleTracePayload] = useState(mockVehicleTraceData);

  // Navigation router handler
  const handleNavigate = (route: NavRoute | string) => {
    if (route === 'dashboard' || route === 'vehicle-trace' || route === 'home') {
      setCurrentRoute(route as NavRoute | 'home');
    }
  };

  // Quick plate search handler from Dashboard header
  const handleSearchPlate = (plateQuery: string) => {
    setVehicleTracePayload((prev) => ({
      ...prev,
      searchedPlate: plateQuery,
    }));
    setCurrentRoute('vehicle-trace');
  };

  // View specific plate trajectory from alert card or model analysis card
  const handleViewTrace = (plateNumber: string) => {
    setVehicleTracePayload((prev) => ({
      ...prev,
      searchedPlate: plateNumber,
    }));
    setCurrentRoute('vehicle-trace');
  };

  const isHomeScreen = currentRoute === 'home';

  return (
    <div className="min-h-screen bg-[#151515] text-white flex flex-col font-sans select-none overflow-x-hidden">
      {/* Top Navigation Bar: Rendered ONLY on non-home pages (Dashboard & Vehicle Trace) */}
      {!isHomeScreen && (
        <Header 
          currentRoute={currentRoute} 
          onNavigate={handleNavigate} 
        />
      )}

      {/* Main Body Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Rendered ONLY on non-home pages (Dashboard & Vehicle Trace) */}
        {!isHomeScreen && (
          <Sidebar 
            currentRoute={currentRoute as NavRoute} 
            onNavigate={handleNavigate}
          />
        )}

        {/* Dynamic Screen View Content Area */}
        <main className={`flex-1 overflow-y-auto bg-[#151515] ${isHomeScreen ? 'p-0' : 'p-4 md:p-6'}`}>
          {currentRoute === 'home' && (
            <HomeView onNavigate={handleNavigate} />
          )}

          {currentRoute === 'dashboard' && (
            <DashboardView
              data={mockDashboardData}
              onSearchPlate={handleSearchPlate}
              onViewTrace={handleViewTrace}
              onNavigateSection={(section) => handleNavigate(section as NavRoute)}
            />
          )}

          {currentRoute === 'vehicle-trace' && (
            <VehicleTraceView
              data={vehicleTracePayload}
              onSearchPlate={handleSearchPlate}
            />
          )}
        </main>
      </div>

      {/* Footer */}
      {!isHomeScreen && (
        <footer className="bg-[#151515] py-2.5 px-4 text-center select-none z-20 border-t border-white/5">
          <p className="text-[11px] text-[#A0A0A0] font-body">
            © 2026 TRACE — Tracking, Recognition, Analytics & City-wide Traffic Enforcement. All Rights Reserved.
          </p>
        </footer>
      )}
    </div>
  );
};

export default App;
