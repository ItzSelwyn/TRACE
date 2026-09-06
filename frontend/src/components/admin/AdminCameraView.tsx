import React, { useEffect, useState } from 'react';

interface CameraItem {
  camera_id: string;
  name: string;
  source_type: string;
  source_path: string;
  scenario: string;
  fps: number;
  enabled: boolean;
  sync_offset_s: number;
  frame_count?: number;
  total_frames?: number;
  status: string;
  sync_mode: string;
  current_frame: number;
  current_local_time: number;
}

interface PlaybackStatus {
  sync_mode: string;
  playback_state: string;
  playback_speed: number;
  master_time_s: number;
  master_time_formatted: string;
  max_duration_s?: number;
  max_duration_formatted?: string;
  loop_scenario: boolean;
}

interface DiscoveredSourceVideo {
  id: string;
  path: string;
  filename: string;
  relative_path: string;
  scenario: string;
  camera_id?: string;
  resolution: string;
  fps: number;
  frame_count: number;
  duration_s: number;
  sync_offset_s?: number;
  size_bytes: number;
}

interface DiscoveredSourceImage {
  id: string;
  path: string;
  filename: string;
  relative_path: string;
  scenario: string;
  resolution: string;
  format: string;
  size_bytes: number;
}

interface DiscoveredSources {
  videos: DiscoveredSourceVideo[];
  images: DiscoveredSourceImage[];
  scenarios: Record<string, Record<string, { start_timestamp_s: number; frame_count?: number }>>;
}

interface DebugResult {
  image_path: string;
  dimensions: string;
  vehicle_detected: boolean;
  vehicle_type: string;
  vehicle_confidence?: number;
  vehicle_colour: string;
  plate_detected: boolean;
  plate_number: string;
  ocr_confidence?: number;
  original_image_b64: string;
  yolo_annotated_b64: string;
  vehicle_crop_b64: string;
  plate_crop_b64: string;
}

const DEFAULT_CAMERAS: CameraItem[] = [
  {
    camera_id: 'c020',
    name: 'Camera 020',
    source_type: 'video',
    source_path: 'footage/c020/vdo.avi',
    scenario: 'S04',
    fps: 10.0,
    enabled: true,
    sync_offset_s: 25.905,
    frame_count: 473,
    total_frames: 473,
    status: 'PROCESSING',
    sync_mode: 'synchronized',
    current_frame: 0,
    current_local_time: 0.0,
  },
  {
    camera_id: 'c023',
    name: 'Camera 023',
    source_type: 'video',
    source_path: 'footage/c023/vdo.avi',
    scenario: 'S04',
    fps: 10.0,
    enabled: true,
    sync_offset_s: 45.716,
    frame_count: 609,
    total_frames: 609,
    status: 'PROCESSING',
    sync_mode: 'synchronized',
    current_frame: 0,
    current_local_time: 0.0,
  },
  {
    camera_id: 'c029',
    name: 'Camera 029',
    source_type: 'video',
    source_path: 'footage/c029/vdo.avi',
    scenario: 'S04',
    fps: 10.0,
    enabled: true,
    sync_offset_s: 125.788,
    frame_count: 260,
    total_frames: 260,
    status: 'WAITING',
    sync_mode: 'synchronized',
    current_frame: 0,
    current_local_time: 0.0,
  },
  {
    camera_id: 'c035',
    name: 'Camera 035',
    source_type: 'video',
    source_path: 'footage/c035/vdo.avi',
    scenario: 'S04',
    fps: 10.0,
    enabled: true,
    sync_offset_s: 165.568,
    frame_count: 210,
    total_frames: 210,
    status: 'WAITING',
    sync_mode: 'synchronized',
    current_frame: 0,
    current_local_time: 0.0,
  },
];

const DEFAULT_PLAYBACK: PlaybackStatus = {
  sync_mode: 'synchronized',
  playback_state: 'playing',
  playback_speed: 1.0,
  master_time_s: 0.0,
  master_time_formatted: '00:00.000',
  max_duration_s: 190.0,
  max_duration_formatted: '03:10.000',
  loop_scenario: true,
};

export const AdminCameraView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'cameras' | 'debugger'>('cameras');
  const [cameras, setCameras] = useState<CameraItem[]>(DEFAULT_CAMERAS);
  const [playback, setPlayback] = useState<PlaybackStatus>(DEFAULT_PLAYBACK);
  const [sources, setSources] = useState<DiscoveredSources | null>(null);

  // Smooth live ticking master clock (advances smoothly in real time)
  const [liveMasterTime, setLiveMasterTime] = useState<number>(0.0);

  // Modal State for Changing Camera Source
  const [modalCamera, setModalCamera] = useState<CameraItem | null>(null);
  const [selectedSourceType, setSelectedSourceType] = useState<'video' | 'image'>('video');
  const [selectedSourcePath, setSelectedSourcePath] = useState<string>('');
  const [customPath, setCustomPath] = useState<string>('');
  const [isApplying, setIsApplying] = useState<boolean>(false);

  // Modal State for Camera Snapshot Preview
  const [previewData, setPreviewData] = useState<{
    camera_id: string;
    name: string;
    status: string;
    source_type: string;
    source_path: string;
    current_frame_idx: number;
    total_frames: number;
    preview_b64: string;
  } | null>(null);

  // Model Visual Debugger State
  const [debugImageInput, setDebugImageInput] = useState<string>('');
  const [debugResult, setDebugResult] = useState<DebugResult | null>(null);
  const [isDebugRunning, setIsDebugRunning] = useState<boolean>(false);
  const [debugError, setDebugError] = useState<string | null>(null);

  const formatLiveTime = (seconds: number) => {
    const s = Math.max(0, seconds);
    const mins = Math.floor(s / 60);
    const secs = Math.floor(s % 60);
    const millis = Math.floor((s - Math.floor(s)) * 1000);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(millis).padStart(3, '0')}`;
  };

  // Sync liveMasterTime whenever server updates
  useEffect(() => {
    if (playback?.master_time_s !== undefined) {
      setLiveMasterTime(playback.master_time_s);
    }
  }, [playback?.master_time_s]);

  // High-resolution local clock ticker (every 50ms) for ultra-smooth UI
  useEffect(() => {
    if (playback?.playback_state !== 'playing') return;
    const speed = playback?.playback_speed || 1.0;
    const maxDur = playback?.max_duration_s || 190.0;
    const tickInterval = 50;

    const timer = setInterval(() => {
      setLiveMasterTime((prev) => {
        const next = prev + (tickInterval / 1000) * speed;
        if (next >= maxDur) {
          return playback.loop_scenario ? 0.0 : maxDur;
        }
        return next;
      });
    }, tickInterval);

    return () => clearInterval(timer);
  }, [playback?.playback_state, playback?.playback_speed, playback?.max_duration_s, playback?.loop_scenario]);

  // Fetch initial data and poll at 1000ms
  const fetchData = async () => {
    try {
      const [camsRes, playRes, srcRes] = await Promise.all([
        fetch('/admin/cameras'),
        fetch('/admin/playback/status'),
        fetch('/admin/sources'),
      ]);

      if (camsRes.ok) {
        const camsData = await camsRes.json();
        if (camsData.cameras?.length > 0) {
          setCameras(camsData.cameras);
        }
      }
      if (playRes.ok) {
        const playData = await playRes.json();
        if (playData?.playback_state) {
          setPlayback((prev) => ({ ...prev, ...playData }));
        }
      }
      if (srcRes.ok) {
        const srcData = await srcRes.json();
        setSources(srcData.data || null);
        if (srcData.data?.images?.length > 0 && !debugImageInput) {
          setDebugImageInput(srcData.data.images[0].path || srcData.data.images[0].relative_path);
        }
      }
    } catch (err) {
      console.error('Error loading admin data:', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(async () => {
      try {
        const [camsRes, playRes] = await Promise.all([
          fetch('/admin/cameras'),
          fetch('/admin/playback/status'),
        ]);
        if (camsRes.ok) {
          const cd = await camsRes.json();
          if (cd.cameras?.length > 0) {
            setCameras(cd.cameras);
          }
        }
        if (playRes.ok) {
          const pd = await playRes.json();
          if (pd?.playback_state) {
            setPlayback((prev) => ({ ...prev, ...pd }));
          }
        }
      } catch (e) {
        // silent catch
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Playback handlers
  const handleTogglePlay = async () => {
    const nextState = playback.playback_state === 'playing' ? 'paused' : 'playing';
    setPlayback((prev) => ({ ...prev, playback_state: nextState }));
    try {
      const res = await fetch('/admin/playback/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ playback_state: nextState }),
      });
      if (res.ok) {
        const d = await res.json();
        setPlayback((prev) => ({ ...prev, ...d.playback }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleResetPlayback = async () => {
    setLiveMasterTime(0.0);
    setPlayback((prev) => ({ ...prev, master_time_s: 0.0, master_time_formatted: '00:00.000' }));
    try {
      const res = await fetch('/admin/playback/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seek_time_s: 0.0 }),
      });
      if (res.ok) {
        const d = await res.json();
        setPlayback((prev) => ({ ...prev, ...d.playback }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleChangeSpeed = async (speed: number) => {
    setPlayback((prev) => ({ ...prev, playback_speed: speed }));
    try {
      const res = await fetch('/admin/playback/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ playback_speed: speed }),
      });
      if (res.ok) {
        const d = await res.json();
        setPlayback((prev) => ({ ...prev, ...d.playback }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleSyncMode = async () => {
    const nextMode = playback.sync_mode === 'synchronized' ? 'independent' : 'synchronized';
    setPlayback((prev) => ({ ...prev, sync_mode: nextMode }));
    try {
      const res = await fetch('/admin/playback/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sync_mode: nextMode }),
      });
      if (res.ok) {
        const d = await res.json();
        setPlayback((prev) => ({ ...prev, ...d.playback }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleLoop = async () => {
    const nextLoop = !playback.loop_scenario;
    setPlayback((prev) => ({ ...prev, loop_scenario: nextLoop }));
    try {
      const res = await fetch('/admin/playback/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ loop_scenario: nextLoop }),
      });
      if (res.ok) {
        const d = await res.json();
        setPlayback((prev) => ({ ...prev, ...d.playback }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Camera Actions
  const handleToggleEnable = async (camera: CameraItem) => {
    const endpoint = camera.enabled
      ? `/admin/cameras/${camera.camera_id}/disable`
      : `/admin/cameras/${camera.camera_id}/enable`;
    try {
      const res = await fetch(endpoint, { method: 'POST' });
      if (res.ok) {
        const d = await res.json();
        setCameras((prev) =>
          prev.map((c) => (c.camera_id === camera.camera_id ? d.camera : c))
        );
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleOpenSourceModal = (camera: CameraItem) => {
    setModalCamera(camera);
    setSelectedSourceType(camera.source_type === 'image' ? 'image' : 'video');
    setSelectedSourcePath(camera.source_path);
    setCustomPath('');
  };

  const handleApplySource = async () => {
    if (!modalCamera) return;
    const finalPath = customPath.trim() || selectedSourcePath;
    if (!finalPath) return;

    setIsApplying(true);
    try {
      const res = await fetch(`/admin/cameras/${modalCamera.camera_id}/source`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: finalPath,
          source_type: selectedSourceType,
        }),
      });
      if (res.ok) {
        const d = await res.json();
        setCameras((prev) =>
          prev.map((c) => (c.camera_id === modalCamera.camera_id ? d.camera : c))
        );
        setModalCamera(null);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsApplying(false);
    }
  };

  const handleOpenPreview = async (camera: CameraItem) => {
    try {
      const res = await fetch(`/admin/cameras/${camera.camera_id}/preview`);
      if (res.ok) {
        const d = await res.json();
        setPreviewData(d);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Run Debug Pipeline on Test Image
  const handleRunDebug = async () => {
    if (!debugImageInput.trim()) return;
    setIsDebugRunning(true);
    setDebugError(null);
    try {
      const res = await fetch('/admin/debug/test-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_path: debugImageInput.trim() }),
      });
      if (res.ok) {
        const d = await res.json();
        setDebugResult(d.result);
      } else {
        const err = await res.json();
        setDebugError(err.detail || 'Debug test failed');
      }
    } catch (e: any) {
      setDebugError(e.message || 'Network error');
    } finally {
      setIsDebugRunning(false);
    }
  };

  // Standardized TRACE Status Badges
  const getStatusBadge = (status: string, isWaiting: boolean, isEnded: boolean) => {
    if (isWaiting) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[3px] text-xs font-heading font-bold bg-[#B8860B]/20 text-[#B8860B]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#B8860B]" />
          STANDBY
        </span>
      );
    }
    if (isEnded) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[3px] text-xs font-heading font-bold bg-[#971D1B]/20 text-[#971D1B]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#971D1B]" />
          ENDED
        </span>
      );
    }

    switch (status.toUpperCase()) {
      case 'PROCESSING':
      case 'ONLINE':
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[3px] text-xs font-heading font-bold bg-[#1B7A43]/20 text-[#1B7A43]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1B7A43]" />
            PROCESSING
          </span>
        );
      case 'WAITING':
      case 'STANDBY':
      case 'PAUSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[3px] text-xs font-heading font-bold bg-[#B8860B]/20 text-[#B8860B]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#B8860B]" />
            {status.toUpperCase()}
          </span>
        );
      case 'SOURCE ENDED':
      case 'DISABLED':
      case 'DOWN':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[3px] text-xs font-heading font-bold bg-[#971D1B]/20 text-[#971D1B]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#971D1B]" />
            {status.toUpperCase()}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[3px] text-xs font-heading font-bold bg-[#151515] text-[#A0A0A0]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#A0A0A0]" />
            {status.toUpperCase()}
          </span>
        );
    }
  };

  const maxScenarioDuration = playback?.max_duration_s || 190.0;
  const maxDurationFormatted = playback?.max_duration_formatted || '03:10.000';

  return (
    <div className="space-y-5 pb-8 font-body select-none">
      {/* Top Banner & Tab Navigation */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-[#1E1E1E] p-4 rounded-[3px] shadow-lg">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-6 bg-[#F2D04E] rounded-[3px]" />
            <h1 className="text-xl font-bold font-heading uppercase tracking-wider text-white">
              Admin Camera & Scenario Control
            </h1>
            <span className="px-2 py-0.5 bg-[#F2D04E]/10 text-[#F2D04E] text-[11px] font-heading font-bold rounded-[3px]">
              ADMIN / DEV
            </span>
          </div>
          <p className="text-xs text-[#AEA793] font-heading mt-1 ml-5">
            Dynamically switch camera inputs, synchronize CityFlow multi-camera scenario timing, and inspect perception model crops.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-2 bg-[#151515] p-1.5 rounded-[3px]">
          <button
            onClick={() => setActiveTab('cameras')}
            className={`px-4 py-2 rounded-[3px] text-xs font-heading font-bold uppercase tracking-wider transition-colors cursor-pointer ${
              activeTab === 'cameras'
                ? 'bg-[#F2D04E] text-[#000000]'
                : 'text-[#AEA793] hover:text-white hover:bg-white/5'
            }`}
          >
            Camera & Playback
          </button>
          <button
            onClick={() => setActiveTab('debugger')}
            className={`px-4 py-2 rounded-[3px] text-xs font-heading font-bold uppercase tracking-wider transition-colors cursor-pointer ${
              activeTab === 'debugger'
                ? 'bg-[#F2D04E] text-[#000000]'
                : 'text-[#AEA793] hover:text-white hover:bg-white/5'
            }`}
          >
            Model Visual Debugger
          </button>
        </div>
      </div>

      {/* TAB 1: CAMERA & PLAYBACK CONTROL */}
      {activeTab === 'cameras' && (
        <>
          {/* Master Timeline & Synchronization Bar */}
          <div className="bg-[#1E1E1E] p-4 rounded-[3px] shadow-lg space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-3 border-b border-[#AEA793]/20">
              {/* Digital Master Clock */}
              <div className="flex items-center gap-4">
                <div className="bg-[#151515] px-4 py-2 rounded-[3px]">
                  <div className="text-[10px] text-[#AEA793] font-heading font-bold uppercase tracking-wider">
                    Master Scenario Timeline (T_master)
                  </div>
                  <div className="text-2xl font-heading font-bold text-[#F2D04E] tracking-wider">
                    {formatLiveTime(liveMasterTime)}
                  </div>
                </div>

                <div className="text-xs space-y-1 font-heading">
                  <div className="text-[#AEA793]">
                    Mode:{' '}
                    <span className="font-bold text-white">
                      {playback?.sync_mode === 'synchronized'
                        ? 'CityFlow S04 Synchronized'
                        : 'Independent Camera Playback'}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#AEA793]">
                    Formula: T_local(cam) = T_master - T_start(cam)
                  </div>
                </div>
              </div>

              {/* Master Playback Controls */}
              <div className="flex flex-wrap items-center gap-2.5">
                {/* Play / Pause */}
                <button
                  onClick={handleTogglePlay}
                  className="px-4 py-2 bg-[#F2D04E] text-[#000000] font-heading font-bold text-xs uppercase tracking-wider rounded-[3px] flex items-center gap-2 shadow-md cursor-pointer transition-colors"
                >
                  {playback?.playback_state === 'playing' ? (
                    <>
                      <span>⏸</span> PAUSE SCENARIO
                    </>
                  ) : (
                    <>
                      <span>▶</span> PLAY SCENARIO
                    </>
                  )}
                </button>

                {/* Reset to 00:00 */}
                <button
                  onClick={handleResetPlayback}
                  className="px-3 py-2 bg-[#151515] hover:bg-white/5 text-[#A0A0A0] hover:text-white font-heading font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors"
                >
                  ⏮ RESET 00:00
                </button>

                {/* Speed Multipliers */}
                <div className="flex items-center bg-[#151515] p-1 rounded-[3px]">
                  {[0.25, 0.5, 1.0, 2.0, 4.0].map((spd) => (
                    <button
                      key={spd}
                      onClick={() => handleChangeSpeed(spd)}
                      className={`px-2 py-1 text-[11px] font-heading font-bold rounded-[3px] cursor-pointer transition-colors ${
                        playback?.playback_speed === spd
                          ? 'bg-[#F2D04E] text-[#000000]'
                          : 'text-[#AEA793] hover:text-white'
                      }`}
                    >
                      {spd}x
                    </button>
                  ))}
                </div>

                {/* Sync Mode Toggle */}
                <button
                  onClick={handleToggleSyncMode}
                  className={`px-3 py-2 text-xs font-heading font-bold uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors ${
                    playback?.sync_mode === 'synchronized'
                      ? 'bg-[#1B7A43]/20 text-[#1B7A43]'
                      : 'bg-[#B8860B]/20 text-[#B8860B]'
                  }`}
                  title="Toggle between synchronized multi-camera timeline vs independent playback"
                >
                  {playback?.sync_mode === 'synchronized' ? 'SYNC: ON (S04)' : 'INDEPENDENT'}
                </button>

                {/* Loop Scenario Toggle */}
                <button
                  onClick={handleToggleLoop}
                  className={`px-3 py-2 text-xs font-heading font-bold uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors ${
                    playback?.loop_scenario
                      ? 'bg-[#F2D04E]/20 text-[#F2D04E]'
                      : 'bg-[#151515] text-[#A0A0A0]'
                  }`}
                >
                  LOOP: {playback?.loop_scenario ? 'ON' : 'OFF'}
                </button>
              </div>
            </div>

            {/* Visual Timeline Progress Bar */}
            <div className="space-y-1 font-heading">
              <div className="flex justify-between text-[10px] text-[#AEA793]">
                <span>00:00 (Scenario Start)</span>
                <span>
                  Active: {formatLiveTime(liveMasterTime)} / {maxDurationFormatted} (CityFlow S04)
                </span>
                <span>{maxDurationFormatted.substring(0, 5)} (Scenario End)</span>
              </div>
              <div className="w-full h-2 bg-[#151515] rounded-[3px] overflow-hidden relative">
                <div
                  className="h-full bg-[#F2D04E] transition-all duration-100"
                  style={{
                    width: `${Math.min(100, (liveMasterTime / maxScenarioDuration) * 100)}%`,
                  }}
                />
              </div>
            </div>
          </div>

          {/* 4 Camera Stream Configuration Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {cameras.map((cam) => {
              const isEnabled = cam.enabled;
              const isSynchronized = playback.sync_mode === 'synchronized';
              const isWaiting = isSynchronized && liveMasterTime < cam.sync_offset_s;
              const videoDuration = (cam.total_frames || 400) / cam.fps;
              const isEnded = isSynchronized && liveMasterTime >= (cam.sync_offset_s + videoDuration);
              const computedLocalTime = isWaiting
                ? 0.0
                : Math.min(videoDuration, Math.max(0.0, liveMasterTime - cam.sync_offset_s));

              return (
                <div
                  key={cam.camera_id}
                  className={`bg-[#1E1E1E] rounded-[3px] p-4 shadow-md flex flex-col justify-between ${
                    isEnabled ? 'opacity-100' : 'opacity-70'
                  }`}
                >
                  {/* Card Header */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-[#151515] text-[#F2D04E] font-heading font-bold text-xs rounded-[3px]">
                          {cam.camera_id.toUpperCase()}
                        </span>
                        <h3 className="font-bold text-sm text-white font-heading">{cam.name}</h3>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusBadge(cam.status, isWaiting, isEnded)}
                      </div>
                    </div>

                    {/* Stream Thumbnail / Feed Preview (Strict 16:9 Aspect Ratio) */}
                    <div className="relative bg-[#000000] rounded-[3px] overflow-hidden aspect-video mb-3">
                      {isEnabled ? (
                        <img
                          src={`/perception/camera/${cam.camera_id}/feed`}
                          alt={cam.name}
                          className="w-full h-full object-contain bg-[#000000]"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      ) : (
                        <div className="w-full h-full flex flex-col items-center justify-center text-[#AEA793] space-y-2">
                          <span className="text-xl">🛑</span>
                          <span className="text-xs font-heading font-bold uppercase tracking-wider">
                            Camera Feed Disabled
                          </span>
                        </div>
                      )}

                      {/* Video Stream Info Overlay */}
                      <div className="absolute top-2 left-2 bg-[#151515]/90 px-2 py-1 rounded-[3px] text-[10px] font-heading text-[#AEA793]">
                        {cam.source_type.toUpperCase()}: {cam.source_path.split('/').pop()}
                      </div>

                      <div className="absolute bottom-2 right-2 bg-[#151515]/90 px-2 py-1 rounded-[3px] text-[10px] font-heading text-[#F2D04E]">
                        FPS: {cam.fps} | Frame: {cam.current_frame} / {cam.total_frames || 'N/A'}
                      </div>
                    </div>

                    {/* Timing & Source Details */}
                    <div className="grid grid-cols-2 gap-2 bg-[#151515] p-2.5 rounded-[3px] text-xs mb-3 font-heading">
                      <div>
                        <span className="text-[#AEA793] block text-[10px] uppercase font-bold">
                          Scenario / Offset
                        </span>
                        <span className="text-white font-semibold">
                          {cam.scenario} (T_start: +{cam.sync_offset_s.toFixed(3)}s)
                        </span>
                      </div>
                      <div>
                        <span className="text-[#AEA793] block text-[10px] uppercase font-bold">
                          Local Time (T_local)
                        </span>
                        <span className="text-[#F2D04E] font-bold">
                          {isWaiting
                            ? `WAITING (-${(cam.sync_offset_s - liveMasterTime).toFixed(1)}s)`
                            : isEnded
                            ? `ENDED (${videoDuration.toFixed(1)}s)`
                            : `${computedLocalTime.toFixed(2)}s`}
                        </span>
                      </div>
                      <div className="col-span-2 pt-1 border-t border-[#AEA793]/20 truncate">
                        <span className="text-[#AEA793] text-[10px] uppercase font-bold mr-1">
                          Source:
                        </span>
                        <span className="text-white/80 text-[11px] truncate">
                          {cam.source_path}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Card Actions */}
                  <div className="flex items-center gap-2 pt-2 border-t border-[#AEA793]/20">
                    <button
                      onClick={() => handleOpenSourceModal(cam)}
                      className="flex-1 py-2 px-3 bg-[#F2D04E] text-[#000000] font-heading font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors flex items-center justify-center gap-1.5"
                    >
                      <span>🔄</span> Change Input
                    </button>

                    <button
                      onClick={() => handleOpenPreview(cam)}
                      className="py-2 px-3 bg-[#151515] hover:bg-white/5 text-white font-heading font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors"
                      title="Inspect full resolution snapshot"
                    >
                      📷 Snapshot
                    </button>

                    <button
                      onClick={() => handleToggleEnable(cam)}
                      className={`py-2 px-3 font-heading font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors ${
                        isEnabled
                          ? 'bg-[#971D1B]/20 text-[#971D1B]'
                          : 'bg-[#1B7A43]/20 text-[#1B7A43]'
                      }`}
                    >
                      {isEnabled ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* TAB 2: MODEL VISUAL DEBUGGER (Image OCR & Colour Crop Inspector) */}
      {activeTab === 'debugger' && (
        <div className="bg-[#1E1E1E] p-5 rounded-[3px] shadow-lg space-y-6">
          <div>
            <h2 className="text-base font-bold font-heading uppercase tracking-wider text-white flex items-center gap-2">
              <span className="w-2 h-4 bg-[#F2D04E] rounded-[3px]" />
              Perception Model Visual Crop & Attribute Debugger
            </h2>
            <p className="text-xs text-[#AEA793] font-heading mt-1 ml-4">
              Select any test image from <code className="text-[#F2D04E]">data/</code> to inspect real YOLO vehicle localization, color classifier crops, and PaddleOCR license plate recognition results side-by-side.
            </p>
          </div>

          {/* Test Image Selector Bar */}
          <div className="bg-[#151515] p-4 rounded-[3px] flex flex-col md:flex-row items-stretch md:items-center gap-3">
            <div className="flex-1 space-y-1">
              <label className="text-[11px] font-heading font-bold uppercase tracking-wider text-[#AEA793]">
                Select Discovered Test Image:
              </label>
              <select
                value={debugImageInput}
                onChange={(e) => setDebugImageInput(e.target.value)}
                className="w-full bg-[#1E1E1E] text-white rounded-[3px] px-3 py-2 text-xs font-heading focus:outline-none"
              >
                {sources?.images.map((img) => (
                  <option key={img.id} value={img.path || img.relative_path}>
                    {img.path || img.relative_path} ({img.resolution})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex-1 space-y-1">
              <label className="text-[11px] font-heading font-bold uppercase tracking-wider text-[#AEA793]">
                Or Enter Relative Path under data/:
              </label>
              <input
                type="text"
                value={debugImageInput}
                onChange={(e) => setDebugImageInput(e.target.value)}
                placeholder="e.g. TN/2.jpg or test1.jpg"
                className="w-full bg-[#1E1E1E] text-white placeholder-[#AEA793] rounded-[3px] px-3 py-2 text-xs font-heading focus:outline-none"
              />
            </div>

            <div className="self-end pt-1">
              <button
                onClick={handleRunDebug}
                disabled={isDebugRunning || !debugImageInput}
                className="w-full md:w-auto px-5 py-2.5 bg-[#F2D04E] text-[#000000] font-heading font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDebugRunning ? 'Processing AI...' : '⚡ Run Perception Pipeline'}
              </button>
            </div>
          </div>

          {debugError && (
            <div className="p-3 bg-[#971D1B]/20 rounded-[3px] text-xs font-heading text-[#971D1B]">
              {debugError}
            </div>
          )}

          {/* Debug Visual Output Panels */}
          {debugResult && (
            <div className="space-y-4">
              {/* Detection Summary Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-[#151515] p-3 rounded-[3px]">
                  <span className="text-[10px] font-heading font-bold uppercase tracking-wider text-[#AEA793] block">
                    Detected Vehicle
                  </span>
                  <div className="text-base font-bold text-white font-heading mt-0.5">
                    {debugResult.vehicle_type}
                  </div>
                  <span className="text-[11px] text-[#F2D04E] font-heading">
                    Conf: {debugResult.vehicle_confidence ? `${(debugResult.vehicle_confidence * 100).toFixed(1)}%` : 'N/A'}
                  </span>
                </div>

                <div className="bg-[#151515] p-3 rounded-[3px]">
                  <span className="text-[10px] font-heading font-bold uppercase tracking-wider text-[#AEA793] block">
                    Classified Colour
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span
                      className="w-3.5 h-3.5 rounded-full"
                      style={{
                        backgroundColor:
                          debugResult.vehicle_colour === 'WHITE'
                            ? '#FFFFFF'
                            : debugResult.vehicle_colour === 'BLACK'
                            ? '#1A1A1A'
                            : debugResult.vehicle_colour === 'SILVER'
                            ? '#A0A0A0'
                            : debugResult.vehicle_colour === 'RED'
                            ? '#971D1B'
                            : debugResult.vehicle_colour === 'BLUE'
                            ? '#3B82F6'
                            : debugResult.vehicle_colour === 'YELLOW'
                            ? '#F2D04E'
                            : debugResult.vehicle_colour === 'GREEN'
                            ? '#1B7A43'
                            : '#888888',
                      }}
                    />
                    <span className="text-base font-bold text-white font-heading">
                      {debugResult.vehicle_colour}
                    </span>
                  </div>
                  <span className="text-[11px] text-[#AEA793] font-heading">HSV + Variance</span>
                </div>

                <div className="bg-[#151515] p-3 rounded-[3px]">
                  <span className="text-[10px] font-heading font-bold uppercase tracking-wider text-[#AEA793] block">
                    PaddleOCR Number Plate
                  </span>
                  <div className="text-base font-heading font-bold text-[#F2D04E] mt-0.5">
                    {debugResult.plate_number}
                  </div>
                  <span className="text-[11px] text-[#AEA793] font-heading">
                    Status: {debugResult.plate_detected ? 'READ' : 'NOT READ'}
                  </span>
                </div>

                <div className="bg-[#151515] p-3 rounded-[3px]">
                  <span className="text-[10px] font-heading font-bold uppercase tracking-wider text-[#AEA793] block">
                    OCR Confidence
                  </span>
                  <div className="text-base font-bold text-white font-heading mt-0.5">
                    {debugResult.ocr_confidence ? `${(debugResult.ocr_confidence * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                  <span className="text-[11px] text-[#AEA793] font-heading">
                    Dims: {debugResult.dimensions}
                  </span>
                </div>
              </div>

              {/* Side-by-Side Visual Crops */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* 1. Full Image + YOLO Bounding Box */}
                <div className="bg-[#151515] p-3 rounded-[3px] flex flex-col">
                  <div className="text-xs font-bold font-heading uppercase text-white mb-2">
                    1. YOLO Detection Overlay
                  </div>
                  <div className="relative bg-[#000000] rounded-[3px] overflow-hidden flex-1 aspect-video flex items-center justify-center">
                    {debugResult.yolo_annotated_b64 ? (
                      <img
                        src={`data:image/jpeg;base64,${debugResult.yolo_annotated_b64}`}
                        alt="YOLO Detection"
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <span className="text-xs text-[#AEA793] font-heading">No detection</span>
                    )}
                  </div>
                </div>

                {/* 2. Vehicle Crop (used for Colour Detection) */}
                <div className="bg-[#151515] p-3 rounded-[3px] flex flex-col">
                  <div className="text-xs font-bold font-heading uppercase text-white mb-2">
                    2. Vehicle Crop (Colour Analysis)
                  </div>
                  <div className="relative bg-[#000000] rounded-[3px] overflow-hidden flex-1 aspect-video flex items-center justify-center">
                    {debugResult.vehicle_crop_b64 ? (
                      <img
                        src={`data:image/jpeg;base64,${debugResult.vehicle_crop_b64}`}
                        alt="Vehicle Crop"
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <span className="text-xs text-[#AEA793] font-heading">No crop</span>
                    )}
                  </div>
                  <div className="mt-2 text-[11px] text-[#AEA793] text-center font-heading">
                    Sampled Region: Vehicle Body Core
                  </div>
                </div>

                {/* 3. Plate Crop (used for PaddleOCR) */}
                <div className="bg-[#151515] p-3 rounded-[3px] flex flex-col">
                  <div className="text-xs font-bold font-heading uppercase text-white mb-2">
                    3. License Plate Crop (PaddleOCR)
                  </div>
                  <div className="relative bg-[#000000] rounded-[3px] overflow-hidden flex-1 aspect-video flex items-center justify-center">
                    {debugResult.plate_crop_b64 ? (
                      <img
                        src={`data:image/jpeg;base64,${debugResult.plate_crop_b64}`}
                        alt="Plate Crop"
                        className="w-full h-full object-contain p-2"
                      />
                    ) : (
                      <span className="text-xs text-[#AEA793] font-heading">No plate crop</span>
                    )}
                  </div>
                  <div className="mt-2 text-[11px] text-[#F2D04E] text-center font-heading font-bold">
                    Extracted: {debugResult.plate_number}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* CHANGE INPUT SOURCE MODAL */}
      {modalCamera && (
        <div className="fixed inset-0 z-50 bg-[#000000]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1E1E1E] rounded-[3px] w-full max-w-2xl overflow-hidden shadow-2xl space-y-4">
            {/* Modal Header */}
            <div className="bg-[#151515] px-5 py-4 border-b border-[#AEA793]/20 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white font-heading uppercase tracking-wider">
                  Change Camera Input Source
                </h3>
                <p className="text-xs text-[#AEA793] font-heading">
                  Select new video or still image for{' '}
                  <span className="text-[#F2D04E] font-bold">
                    {modalCamera.name} ({modalCamera.camera_id.toUpperCase()})
                  </span>
                </p>
              </div>
              <button
                onClick={() => setModalCamera(null)}
                className="text-[#AEA793] hover:text-white text-lg font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-5 space-y-4 max-h-[65vh] overflow-y-auto font-heading">
              {/* Type Switch */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#AEA793]">
                  Input Type:
                </span>
                <div className="flex bg-[#151515] p-1 rounded-[3px]">
                  <button
                    onClick={() => setSelectedSourceType('video')}
                    className={`px-3 py-1 text-xs font-bold uppercase rounded-[3px] cursor-pointer transition-colors ${
                      selectedSourceType === 'video'
                        ? 'bg-[#F2D04E] text-[#000000]'
                        : 'text-[#AEA793] hover:text-white'
                    }`}
                  >
                    Scenario Video
                  </button>
                  <button
                    onClick={() => setSelectedSourceType('image')}
                    className={`px-3 py-1 text-xs font-bold uppercase rounded-[3px] cursor-pointer transition-colors ${
                      selectedSourceType === 'image'
                        ? 'bg-[#F2D04E] text-[#000000]'
                        : 'text-[#AEA793] hover:text-white'
                    }`}
                  >
                    Static Test Image
                  </button>
                </div>
              </div>

              {/* Source Selection List */}
              {selectedSourceType === 'video' ? (
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-[#AEA793] block">
                    Available Discovered Videos in data/:
                  </label>
                  <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                    {sources?.videos.map((vid) => {
                      const isSelected = selectedSourcePath === vid.path;
                      return (
                        <div
                          key={vid.id}
                          onClick={() => setSelectedSourcePath(vid.path)}
                          className={`p-3 rounded-[3px] cursor-pointer transition-colors flex items-center justify-between ${
                            isSelected
                              ? 'bg-[#F2D04E]/15 text-white'
                              : 'bg-[#151515] text-[#AEA793] hover:text-white hover:bg-white/5'
                          }`}
                        >
                          <div>
                            <div className="font-heading text-xs font-bold text-white">{vid.path}</div>
                            <div className="text-[11px] text-[#AEA793]">
                              Scenario: {vid.scenario} | {vid.resolution} @ {vid.fps} FPS ({vid.duration_s}s)
                            </div>
                          </div>
                          {vid.sync_offset_s !== null && vid.sync_offset_s !== undefined && (
                            <span className="px-2 py-0.5 bg-[#151515] text-[#F2D04E] text-[10px] font-heading rounded-[3px]">
                              Offset: +{vid.sync_offset_s}s
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-[#AEA793] block">
                    Available Discovered Images in data/:
                  </label>
                  <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                    {sources?.images.map((img) => {
                      const isSelected = selectedSourcePath === img.path;
                      return (
                        <div
                          key={img.id}
                          onClick={() => setSelectedSourcePath(img.path)}
                          className={`p-3 rounded-[3px] cursor-pointer transition-colors flex items-center justify-between ${
                            isSelected
                              ? 'bg-[#F2D04E]/15 text-white'
                              : 'bg-[#151515] text-[#AEA793] hover:text-white hover:bg-white/5'
                          }`}
                        >
                          <div>
                            <div className="font-heading text-xs font-bold text-white">{img.path}</div>
                            <div className="text-[11px] text-[#AEA793]">
                              Format: {img.format} | Resolution: {img.resolution}
                            </div>
                          </div>
                          <span className="text-[11px] font-heading text-[#AEA793]">
                            {(img.size_bytes / 1024).toFixed(0)} KB
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Custom Path Override Input */}
              <div className="pt-2 border-t border-[#AEA793]/20">
                <label className="text-xs font-bold uppercase tracking-wider text-[#AEA793] block mb-1">
                  Or Custom Relative Path under data/:
                </label>
                <input
                  type="text"
                  value={customPath}
                  onChange={(e) => setCustomPath(e.target.value)}
                  placeholder="e.g. footage/c020/vdo.avi or TN/1.jpg"
                  className="w-full bg-[#151515] text-white placeholder-[#AEA793] rounded-[3px] px-3 py-2 text-xs font-heading focus:outline-none"
                />
              </div>
            </div>

            {/* Modal Footer */}
            <div className="bg-[#151515] px-5 py-3 border-t border-[#AEA793]/20 flex items-center justify-end gap-3 font-heading">
              <button
                onClick={() => setModalCamera(null)}
                className="px-4 py-2 bg-[#151515] hover:bg-white/5 text-[#AEA793] hover:text-white font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleApplySource}
                disabled={isApplying || (!selectedSourcePath && !customPath)}
                className="px-5 py-2 bg-[#F2D04E] text-[#000000] font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isApplying ? 'Applying Hot-Swap...' : 'Apply Input Source'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SNAPSHOT PREVIEW MODAL */}
      {previewData && (
        <div className="fixed inset-0 z-50 bg-[#000000]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1E1E1E] rounded-[3px] w-full max-w-3xl overflow-hidden shadow-2xl space-y-4">
            <div className="bg-[#151515] px-5 py-4 border-b border-[#AEA793]/20 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white font-heading uppercase tracking-wider">
                  Live Snapshot: {previewData.name} ({previewData.camera_id.toUpperCase()})
                </h3>
                <p className="text-xs text-[#AEA793] font-heading">
                  {previewData.source_type.toUpperCase()}: {previewData.source_path} | Frame: {previewData.current_frame_idx} / {previewData.total_frames}
                </p>
              </div>
              <button
                onClick={() => setPreviewData(null)}
                className="text-[#AEA793] hover:text-white text-lg font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="p-5 flex items-center justify-center bg-[#000000] aspect-video">
              {previewData.preview_b64 ? (
                <img
                  src={`data:image/jpeg;base64,${previewData.preview_b64}`}
                  alt="Snapshot"
                  className="max-h-[60vh] object-contain"
                />
              ) : (
                <span className="text-xs text-[#AEA793] font-heading">No frame data</span>
              )}
            </div>

            <div className="bg-[#151515] px-5 py-3 border-t border-[#AEA793]/20 flex items-center justify-between font-heading">
              <span className="text-xs text-[#AEA793]">
                Status: {previewData.status}
              </span>
              <button
                onClick={() => setPreviewData(null)}
                className="px-4 py-2 bg-[#F2D04E] text-[#000000] font-bold text-xs uppercase tracking-wider rounded-[3px] cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
