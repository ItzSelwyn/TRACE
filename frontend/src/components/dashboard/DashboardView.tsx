import React from 'react';
import { DashboardDataPayload } from '../../types/dashboard';
import { TopStatsHeader } from './TopStatsHeader';
import { CameraGrid } from './CameraGrid';
import { ModelAnalysis } from './ModelAnalysis';
import { RecentAlerts } from './RecentAlerts';
import { NetworkAnalysis } from './NetworkAnalysis';

interface DashboardViewProps {
  data: DashboardDataPayload;
  selectedCameraId?: string;
  onSelectCamera?: (cameraId: string) => void;
  onSearchPlate: (plateQuery: string) => void;
  onViewTrace: (plateNumber: string) => void;
  onNavigateSection: (section: 'analytics' | 'alerts' | 'blacklist' | 'cameras') => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  data,
  selectedCameraId = 'c020',
  onSelectCamera,
  onSearchPlate,
  onViewTrace,
  onNavigateSection,
}) => {
  return (
    <div className="space-y-1.5 max-w-[1600px] mx-auto pb-4">
      {/* Top Search & High Level KPI Bar */}
      <TopStatsHeader
        stats={data.topStats}
        onSearch={onSearchPlate}
      />

      {/* Main Dashboard 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-1.5">
        {/* Left Column: 2x2 Camera Grid (7/12 width) */}
        <div className="lg:col-span-7 flex flex-col">
          <CameraGrid
            cameras={data.cameras}
            selectedCameraId={selectedCameraId}
            onSelectCamera={onSelectCamera}
          />
        </div>

        {/* Right Column: Model Analysis Card (5/12 width) */}
        <div className="lg:col-span-5 flex flex-col">
          <ModelAnalysis
            data={data.modelAnalysis}
            selectedCameraId={selectedCameraId}
            onViewTrace={onViewTrace}
          />
        </div>
      </div>

      {/* Bottom Dashboard 2-Column Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-1.5 pt-0.5">
        {/* Left Column: Recent Alerts (7/12 width) */}
        <div className="lg:col-span-7 flex flex-col">
          <RecentAlerts
            alerts={data.recentAlerts}
            onViewAlertTrace={onViewTrace}
            onNavigateAlerts={() => onNavigateSection('alerts')}
          />
        </div>

        {/* Right Column: Network Analysis Stats (5/12 width) */}
        <div className="lg:col-span-5 flex flex-col">
          <NetworkAnalysis
            stats={data.networkStats}
            onNavigateCameras={() => onNavigateSection('cameras')}
          />
        </div>
      </div>
    </div>
  );
};
