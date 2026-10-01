import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { MapProfileConfig, getMapProfile } from '../data/mapProfiles';

export interface DatasetOption {
  id: string;
  label: string;
}

export interface DatasetContextValue {
  activeDataset: string;
  label: string;
  mapProfileKey: string;
  mapProfile: MapProfileConfig;
  availableDatasets: DatasetOption[];
  isSwitching: boolean;
  error: string | null;
  switchDataset: (datasetId: string) => Promise<boolean>;
  refreshDatasetInfo: () => Promise<void>;
}

const DatasetContext = createContext<DatasetContextValue | undefined>(undefined);

export const DatasetProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeDataset, setActiveDataset] = useState<string>('S05');
  const [label, setLabel] = useState<string>('CityFlow S05');
  const [mapProfileKey, setMapProfileKey] = useState<string>('cityflow');
  const [availableDatasets, setAvailableDatasets] = useState<DatasetOption[]>([
    { id: 'S04', label: 'CityFlow S04' },
    { id: 'S05', label: 'CityFlow S05' },
    { id: 'CBE', label: 'Coimbatore CBE' },
  ]);
  const [isSwitching, setIsSwitching] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDatasetInfo = useCallback(async () => {
    try {
      const res = await fetch('/admin/dataset');
      if (res.ok) {
        const data = await res.json();
        if (data.active_dataset) {
          setActiveDataset(data.active_dataset);
          setLabel(data.label || `Dataset ${data.active_dataset}`);
          setMapProfileKey(data.map_profile || 'cityflow');
        }
        if (data.available_datasets && Array.isArray(data.available_datasets)) {
          setAvailableDatasets(data.available_datasets);
        }
      }
    } catch (err) {
      console.warn('Could not fetch dataset info from backend:', err);
    }
  }, []);

  useEffect(() => {
    fetchDatasetInfo();
  }, [fetchDatasetInfo]);

  const switchDataset = useCallback(
    async (datasetId: string): Promise<boolean> => {
      if (isSwitching) return false;
      const targetId = datasetId.toUpperCase().trim();
      if (targetId === activeDataset) return true;

      setIsSwitching(true);
      setError(null);

      try {
        const res = await fetch('/admin/dataset', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataset: targetId }),
        });

        if (!res.ok) {
          let errDetail = 'Failed to switch dataset';
          try {
            const errJson = await res.json();
            if (errJson.detail) errDetail = errJson.detail;
          } catch {
            // fallback text
          }
          setError(errDetail);
          setIsSwitching(false);
          return false;
        }

        const data = await res.json();
        setActiveDataset(data.active_dataset || targetId);
        setLabel(data.label || `Dataset ${targetId}`);
        setMapProfileKey(data.map_profile || (targetId === 'CBE' ? 'coimbatore' : 'cityflow'));
        if (data.available_datasets) {
          setAvailableDatasets(data.available_datasets);
        }

        // Dispatch a window event so any non-React listeners or cache invalidators can react
        window.dispatchEvent(
          new CustomEvent('trace-dataset-switched', {
            detail: {
              active_dataset: data.active_dataset || targetId,
              label: data.label,
              map_profile: data.map_profile,
            },
          })
        );

        setIsSwitching(false);
        return true;
      } catch (err: any) {
        console.warn('Backend unavailable while switching dataset, applying client-side profile:', err);
        setActiveDataset(targetId);
        setLabel(targetId === 'CBE' ? 'Coimbatore CBE' : `CityFlow ${targetId}`);
        setMapProfileKey(targetId === 'CBE' ? 'coimbatore' : 'cityflow');
        window.dispatchEvent(
          new CustomEvent('trace-dataset-switched', {
            detail: {
              active_dataset: targetId,
              label: targetId === 'CBE' ? 'Coimbatore CBE' : `CityFlow ${targetId}`,
              map_profile: targetId === 'CBE' ? 'coimbatore' : 'cityflow',
            },
          })
        );
        setIsSwitching(false);
        return true;
      }
    },
    [activeDataset, isSwitching]
  );

  const mapProfile = getMapProfile(mapProfileKey);

  const value: DatasetContextValue = {
    activeDataset,
    label,
    mapProfileKey,
    mapProfile,
    availableDatasets,
    isSwitching,
    error,
    switchDataset,
    refreshDatasetInfo: fetchDatasetInfo,
  };

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
};

export const useDataset = (): DatasetContextValue => {
  const context = useContext(DatasetContext);
  if (!context) {
    throw new Error('useDataset must be used within a DatasetProvider');
  }
  return context;
};
