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

const API_BASE_URL = (globalThis as { __TRACE_API_BASE_URL__?: string }).__TRACE_API_BASE_URL__ ?? '';

const formatTime = (iso: string) => {
  const date = new Date(iso);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
};

const transformPerceptionStatus = (payload: any, activeCamId: string = 'c020'): DashboardDataPayload => {
  const cameras = Object.entries(payload?.cameras ?? {}).map(([cameraId, camera]: [string, any]) => {
    const status = camera?.camera_status ?? 'online';
    const observations = camera?.observations ?? [];
    const latestObservation = observations[0] ?? null;

    return {
      id: cameraId,
      cameraCode: String(cameraId).toUpperCase(),
      name: `Camera ${cameraId.replace('c', '').toUpperCase()}`,
      location: 'Live Video Feed',
      timestamp: latestObservation?.captured_at ? formatTime(latestObservation.captured_at) : 'Live',
      feedImageUrl: '/assets/Dashboard.png',
      status,
    };
  });

  const onlineCount = cameras.filter((camera) => camera.status === 'online').length;
  const downCount = cameras.filter((camera) => camera.status === 'down').length;
  const activeScans = Object.values(payload?.cameras ?? {}).reduce(
    (total: number, camera: any) => total + ((camera?.observations ?? []).length || 0),
    0
  );

  // Pick top passing vehicle from selected camera
  const targetCamObservations = payload?.cameras?.[activeCamId]?.observations ?? [];
  const selectedObservation = targetCamObservations[0] || cameras
    .map((camera) => payload?.cameras?.[camera.id]?.observations?.[0])
    .find(Boolean);

  return {
    topStats: {
      activeScans: activeScans || 24,
      blacklistsCount: 10,
      systemStatus: downCount > 0 ? 'DEGRADED' : 'OPTIMAL',
    },
    cameras: cameras.length ? cameras : mockDashboardData.cameras,
    modelAnalysis: selectedObservation
      ? {
          cameraId: selectedObservation.camera_id || activeCamId,
          cameraName: `Camera ${String(selectedObservation.camera_id || activeCamId).replace('c', '').toUpperCase()}`,
          location: 'Live Video Feed',
          plateNumber: selectedObservation.fused_plate_text ?? `TRACE-${activeCamId}-1`,
          ocrConfidence: Math.round((selectedObservation.fused_confidence ?? 0.85) * 100),
          vehicleType: (selectedObservation.vehicle_type || 'CAR').toUpperCase(),
          color: (selectedObservation.vehicle_colour || 'WHITE').toUpperCase(),
          timestamp: formatTime(selectedObservation.captured_at),
          detectedImageUrl: '/assets/Dashboard.png',
          boundingLabel: 'Vehicle (YOLOv8)',
        }
      : mockDashboardData.modelAnalysis,
    recentAlerts: [],
    networkStats: {
      uptimeFormatted: '5hrs',
      camerasActive: onlineCount || 4,
      camerasDown: downCount,
      totalCameras: cameras.length || 4,
    },
  };
};

const transformTrajectory = (plate: string, payload: any): VehicleTraceDataPayload => {
  const observations = Array.isArray(payload?.observations) ? payload.observations : [];

  const anomalyCount = payload?.total_anomalies ?? observations.filter(
    (obs: any) => obs.is_impossible_journey || obs.anomaly_type || obs.match_confidence_label === 'candidate'
  ).length;

  return {
    searchedPlate: plate,
    totalScans: observations.length || 4,
    totalAnomalies: anomalyCount,
    selectedTimeWindow: '24hrs',
    chronology: observations.map((obs: any, index: number) => {
      const label: string = obs.match_confidence_label ?? 'confirmed';
      const isAnomaly = obs.is_impossible_journey || obs.anomaly_type;

      let statusMsg = undefined;
      if (obs.is_impossible_journey) {
        statusMsg = `Impossible Journey (${obs.implied_speed_kmph ? Math.round(obs.implied_speed_kmph) + ' km/h' : 'speed ceiling exceeded'})`;
      } else if (obs.anomaly_type) {
        statusMsg = `Anomaly: ${String(obs.anomaly_type).replace('_', ' ')}`;
      } else if (label === 'candidate') {
        statusMsg = `Candidate Match (${((obs.identity_score ?? 0) * 100).toFixed(0)}%)`;
      }

      return {
        id: `obs-${index}`,
        plateNumber: obs.fused_plate_text || plate,
        timestamp: formatTime(obs.captured_at),
        ocrConfidence: Math.round((obs.fused_confidence ?? 0.9) * 100),
        cameraName: obs.camera_name || `Camera ${index + 1}`,
        location: 'Bangalore Road Network',
        trackedTimeAgo: index === 0 ? 'Tracked 2 mins ago' : `Tracked ${index + 1} mins ago`,
        statusType: isAnomaly ? 'anomaly' : 'normal',
        statusMessage: statusMsg,
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
      const isAnomaly = obs.is_impossible_journey || obs.anomaly_type;
      return {
        id: `point-${index}`,
        cameraName: obs.camera_name || `Camera ${index + 1}`,
        location: 'Bangalore Road Network',
        pointType: isAnomaly ? 'anomaly' : index % 3 === 0 ? 'scanned' : 'trajectory',
        xPercent: 15 + index * 22,
        yPercent: 30 + (index % 2) * 20,
      };
    }),
  };
};

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<NavRoute | 'home'>('home');
  const [selectedCameraId, setSelectedCameraId] = useState<string>('c020');
  const [dashboardData, setDashboardData] = useState<DashboardDataPayload>(mockDashboardData);
  const [vehicleTracePayload, setVehicleTracePayload] = useState<VehicleTraceDataPayload>(mockVehicleTraceData);

  useEffect(() => {
    if (currentRoute !== 'dashboard') return;

    let isMounted = true;
    const loadDashboard = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/perception/status`);
        if (!response.ok) return;
        const payload = await response.json();
        if (isMounted) {
          setDashboardData(transformPerceptionStatus(payload, selectedCameraId));
        }
      } catch (err) {
        console.warn('Backend offline, using mock dashboard data:', err);
      }
    };

    loadDashboard();
    const interval = setInterval(loadDashboard, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [currentRoute, selectedCameraId]);

  useEffect(() => {
    if (currentRoute !== 'vehicle-trace') return;

    let isMounted = true;
    const loadVehicleTrace = async () => {
      const plate = vehicleTracePayload.searchedPlate || 'TN 37 CY 1234';
      try {
        const response = await fetch(`${API_BASE_URL}/vehicles/${encodeURIComponent(plate)}/trajectory`);
        if (!response.ok) return;
        const payload = await response.json();
        if (isMounted) {
          setVehicleTracePayload(transformTrajectory(plate, payload));
        }
      } catch (err) {
        console.warn('Backend offline, using mock trajectory data:', err);
      }
    };

    loadVehicleTrace();
    return () => {
      isMounted = false;
    };
  }, [currentRoute, vehicleTracePayload.searchedPlate]);

  const handleNavigate = (route: NavRoute | string) => {
    if (route === 'dashboard' || route === 'vehicle-trace' || route === 'home') {
      setCurrentRoute(route as NavRoute | 'home');
    }
  };

  const handleSelectCamera = (cameraId: string) => {
    setSelectedCameraId(cameraId.toLowerCase());
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
              selectedCameraId={selectedCameraId}
              onSelectCamera={handleSelectCamera}
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
