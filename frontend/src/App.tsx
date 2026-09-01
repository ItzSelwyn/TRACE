import React, { useEffect, useState } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar, NavRoute } from './components/layout/Sidebar';
import { DashboardView } from './components/dashboard/DashboardView';
import { VehicleTraceView } from './components/vehicle-trace/VehicleTraceView';
import { HomeView } from './components/home/HomeView';
import { mockDashboardData } from './data/mockDashboardData';
import { mockVehicleTraceData } from './data/mockVehicleTraceData';
import { DashboardDataPayload } from './types/dashboard';
import { VehicleTraceDataPayload } from './types/vehicleTrace';

const API_BASE_URL = (globalThis as { __TRACE_API_BASE_URL__?: string }).__TRACE_API_BASE_URL__ ?? 'http://localhost:8000';

const formatTime = (iso: string) => {
  const date = new Date(iso);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
};

const transformPerceptionStatus = (payload: any): DashboardDataPayload => {
  const cameras = Object.entries(payload?.cameras ?? {}).map(([cameraId, camera]: [string, any]) => {
    const status = camera?.camera_status ?? 'online';
    const observations = camera?.observations ?? [];
    const latestObservation = observations[0] ?? null;

    return {
      id: cameraId,
      cameraCode: String(cameraId).toUpperCase().replace('C', 'C'),
      name: `Camera ${cameraId.replace('c', '').toUpperCase()}`,
      location: 'Live Feed',
      timestamp: latestObservation?.captured_at ? formatTime(latestObservation.captured_at) : 'Live',
      feedImageUrl: '/assets/Dashboard.png',
      status,
    };
  });

  const onlineCount = cameras.filter((camera) => camera.status === 'online').length;
  const downCount = cameras.filter((camera) => camera.status === 'down').length;
  const activeScans = cameras.reduce((total, camera) => total + ((payload?.cameras?.[camera.id]?.observations ?? []).length || 0), 0);

  const firstObservation = cameras
    .map((camera) => payload?.cameras?.[camera.id]?.observations?.[0])
    .find(Boolean);

  return {
    topStats: {
      activeScans: Math.max(activeScans, 24),
      blacklistsCount: 10,
      systemStatus: downCount > 0 ? 'DEGRADED' : 'OPTIMAL',
    },
    cameras: cameras.length ? cameras : mockDashboardData.cameras,
    modelAnalysis: firstObservation
      ? {
          cameraId: firstObservation.camera_id,
          cameraName: `Camera ${String(firstObservation.camera_id).replace('c', '').toUpperCase()}`,
          location: 'Live Feed',
          plateNumber: firstObservation.fused_plate_text ?? 'TN 01 75 0608',
          ocrConfidence: Math.round((firstObservation.fused_confidence ?? 0.94) * 100),
          vehicleType: 'SUV',
          color: 'Blue',
          timestamp: formatTime(firstObservation.captured_at),
          detectedImageUrl: '/assets/Dashboard.png',
          boundingLabel: 'Vehicle',
        }
      : mockDashboardData.modelAnalysis,
    recentAlerts: [],
    networkStats: {
      uptimeFormatted: '5hrs',
      camerasActive: Math.max(onlineCount, 8),
      camerasDown: Math.max(downCount, 2),
      totalCameras: Math.max(cameras.length || 10, 10),
    },
  };
};

const transformTrajectory = (plate: string, payload: any): VehicleTraceDataPayload => {
  const observations = Array.isArray(payload?.observations) ? payload.observations : [];

  // Count observations with low or no-match confidence for the anomaly badge
  const lowConfidenceCount = observations.filter(
    (obs: any) => obs.match_confidence_label === 'candidate' || obs.match_confidence_label === 'no_match'
  ).length;

  return {
    searchedPlate: plate,
    totalScans: observations.length || 5,
    totalAnomalies: lowConfidenceCount,
    selectedTimeWindow: '24hrs',
    chronology: observations.map((obs: any, index: number) => {
      const label: string = obs.match_confidence_label ?? 'confirmed';
      const isLowConfidence = label === 'candidate' || label === 'no_match';

      return {
        id: `obs-${index}`,
        plateNumber: obs.fused_plate_text || plate,
        timestamp: formatTime(obs.captured_at),
        ocrConfidence: Math.round((obs.fused_confidence ?? 0.9) * 100),
        cameraName: obs.camera_name || `Camera ${index + 1}`,
        location: 'North Highway',
        trackedTimeAgo: index === 0 ? 'Tracked 2 mins ago' : `Tracked ${index + 1} mins ago`,
        statusType: isLowConfidence ? 'anomaly' : 'normal',
        statusMessage: isLowConfidence
          ? `Low Confidence Match (score: ${((obs.identity_score ?? 0) * 100).toFixed(0)}%)`
          : undefined,
        // M3 identity evidence
        identityScore: obs.identity_score ?? undefined,
        confidenceLabel: label as any,
        evidence: obs.evidence
          ? {
              plate_similarity: obs.evidence.plate_similarity,
              ocr_confidence_component: obs.evidence.ocr_confidence_component,
              attribute_match: obs.evidence.attribute_match,
              camera_reliability_weight: obs.evidence.camera_reliability_weight,
            }
          : undefined,
      };
    }),
    mapPoints: observations.map((obs: any, index: number) => {
      const label: string = obs.match_confidence_label ?? 'confirmed';
      const isLowConfidence = label === 'candidate' || label === 'no_match';
      return {
        id: `point-${index}`,
        cameraName: obs.camera_name || `Camera ${index + 1}`,
        location: 'North Highway',
        pointType: isLowConfidence ? 'anomaly' : index % 3 === 0 ? 'scanned' : 'trajectory',
        xPercent: 20 + index * 12,
        yPercent: 30 + index * 9,
      };
    }),
  };
};

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<NavRoute | 'home'>('home');
  const [dashboardData, setDashboardData] = useState<DashboardDataPayload>(mockDashboardData);
  const [vehicleTracePayload, setVehicleTracePayload] = useState<VehicleTraceDataPayload>(mockVehicleTraceData);

  useEffect(() => {
    if (currentRoute !== 'dashboard') return;

    const loadDashboard = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/perception/status`);
        if (!response.ok) return;
        const payload = await response.json();
        setDashboardData(transformPerceptionStatus(payload));
      } catch {
        setDashboardData(mockDashboardData);
      }
    };

    loadDashboard();
  }, [currentRoute]);

  useEffect(() => {
    if (currentRoute !== 'vehicle-trace') return;

    const loadVehicleTrace = async () => {
      const plate = vehicleTracePayload.searchedPlate || 'TN 37 CY 1234';
      try {
        const response = await fetch(`${API_BASE_URL}/vehicles/${encodeURIComponent(plate)}/trajectory`);
        if (!response.ok) return;
        const payload = await response.json();
        setVehicleTracePayload(transformTrajectory(plate, payload));
      } catch {
        setVehicleTracePayload(mockVehicleTraceData);
      }
    };

    loadVehicleTrace();
  }, [currentRoute, vehicleTracePayload.searchedPlate]);

  const handleNavigate = (route: NavRoute | string) => {
    if (route === 'dashboard' || route === 'vehicle-trace' || route === 'home') {
      setCurrentRoute(route as NavRoute | 'home');
    }
  };

  const handleSearchPlate = (plateQuery: string) => {
    setVehicleTracePayload((prev) => ({
      ...prev,
      searchedPlate: plateQuery,
    }));
    setCurrentRoute('vehicle-trace');
  };

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
      {!isHomeScreen && (
        <Header 
          currentRoute={currentRoute} 
          onNavigate={handleNavigate} 
        />
      )}

      <div className="flex-1 flex overflow-hidden">
        {!isHomeScreen && (
          <Sidebar 
            currentRoute={currentRoute as NavRoute} 
            onNavigate={handleNavigate}
          />
        )}

        <main className={`flex-1 overflow-y-auto bg-[#151515] ${isHomeScreen ? 'p-0' : 'p-4 md:p-6'}`}>
          {currentRoute === 'home' && (
            <HomeView onNavigate={handleNavigate} />
          )}

          {currentRoute === 'dashboard' && (
            <DashboardView
              data={dashboardData}
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
