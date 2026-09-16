"""Admin API — Camera Input, Playback, and Perception Scenario Control."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.perception import get_system_uptime
from app.modules.perception.camera_manager import get_camera_manager
from app.modules.perception.source_discovery import discover_sources

logger = logging.getLogger("trace.api.admin")

router = APIRouter(prefix="/admin", tags=["Admin"])


class CameraSourceUpdateRequest(BaseModel):
    source_path: str = Field(..., description="Relative path under data/ to video or image")
    source_type: str = Field("video", description="'video' or 'image'")
    fps: Optional[float] = Field(None, description="Target playback FPS")


class CameraSettingsUpdateRequest(BaseModel):
    name: Optional[str] = None
    fps: Optional[float] = None
    sync_offset_s: Optional[float] = None
    enabled: Optional[bool] = None


class PlaybackSettingsUpdateRequest(BaseModel):
    sync_mode: Optional[str] = Field(None, description="'synchronized' or 'independent'")
    playback_state: Optional[str] = Field(None, description="'playing', 'paused', or 'stopped'")
    playback_speed: Optional[float] = Field(None, description="0.25 to 4.0")
    loop_scenario: Optional[bool] = None
    seek_time_s: Optional[float] = None


class DebugImageRequest(BaseModel):
    image_path: str = Field(..., description="Path under data/ to test image")


class DatasetSwitchRequest(BaseModel):
    dataset: str = Field(..., description="'S04', 'S05', or 'CBE'")


@router.get("/dataset")
def get_active_dataset():
    """Return the currently active dataset and available options."""
    mgr = get_camera_manager()
    return mgr.get_active_dataset_info()


@router.put("/dataset")
def switch_active_dataset(req: DatasetSwitchRequest):
    """Switch the global active dataset to S04, S05, or CBE."""
    mgr = get_camera_manager()
    try:
        updated_info = mgr.switch_dataset(req.dataset)
        return updated_info
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fe:
        raise HTTPException(status_code=400, detail=str(fe))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.error(f"Failed to switch dataset to '{req.dataset}': {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error switching dataset: {e}")


@router.get("/cameras")
def list_cameras():
    """Return all managed cameras and their runtime status."""
    mgr = get_camera_manager()
    cams = mgr.list_cameras()
    active = sum(1 for c in cams if c.get("enabled", True) and c.get("status") not in ["DISABLED", "FAILED", "OFFLINE"])
    down = len(cams) - active
    uptime_secs, uptime_formatted, uptime_hours = get_system_uptime()
    return {
        "status": "ok",
        "cameras": cams,
        "count": len(cams),
        "total_cameras": len(cams),
        "active_cameras": active,
        "down_cameras": down,
        "uptime_seconds": uptime_secs,
        "uptime_formatted": uptime_formatted,
        "uptime_hours": uptime_hours,
    }


@router.get("/sources")
def get_discovered_sources():
    """Scan and return all available video and image assets under data/."""
    try:
        data = discover_sources()
        return {
            "status": "ok",
            "data": data,
        }
    except Exception as e:
        logger.error(f"Error discovering sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/cameras/{camera_id}/source")
def update_camera_source(camera_id: str, req: CameraSourceUpdateRequest):
    """Hot-swap the input source of a camera to a video or static image."""
    mgr = get_camera_manager()
    try:
        updated = mgr.update_camera_source(
            camera_id=camera_id,
            source_path=req.source_path,
            source_type=req.source_type,
            fps=req.fps,
        )
        return {
            "status": "ok",
            "camera": updated,
            "message": f"Camera {camera_id} source updated to {req.source_path}",
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating camera source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/cameras/{camera_id}/settings")
def update_camera_settings(camera_id: str, req: CameraSettingsUpdateRequest):
    """Update runtime camera parameters."""
    mgr = get_camera_manager()
    try:
        updated = mgr.update_camera_settings(
            camera_id=camera_id,
            name=req.name,
            fps=req.fps,
            sync_offset_s=req.sync_offset_s,
            enabled=req.enabled,
        )
        return {
            "status": "ok",
            "camera": updated,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating camera settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cameras/{camera_id}/enable")
def enable_camera(camera_id: str):
    """Enable camera processing."""
    mgr = get_camera_manager()
    try:
        updated = mgr.set_camera_enabled(camera_id, True)
        return {
            "status": "ok",
            "camera": updated,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/cameras/{camera_id}/disable")
def disable_camera(camera_id: str):
    """Disable camera processing."""
    mgr = get_camera_manager()
    try:
        updated = mgr.set_camera_enabled(camera_id, False)
        return {
            "status": "ok",
            "camera": updated,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/cameras/{camera_id}/preview")
def get_camera_preview(camera_id: str):
    """Return an instant snapshot frame and live metadata."""
    mgr = get_camera_manager()
    try:
        return mgr.get_camera_preview(camera_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error getting preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug/test-image")
def debug_test_image(req: DebugImageRequest):
    """Run full production perception on a static test image and return visual crops."""
    mgr = get_camera_manager()
    try:
        result = mgr.debug_test_image(req.image_path)
        return {
            "status": "ok",
            "result": result,
        }
    except FileNotFoundError as fe:
        raise HTTPException(status_code=404, detail=str(fe))
    except Exception as e:
        logger.error(f"Error in debug_test_image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/playback/status")
def get_playback_status():
    """Return the master timeline and synchronization status."""
    mgr = get_camera_manager()
    return mgr.controller.get_status()


@router.patch("/playback/settings")
def update_playback_settings(req: PlaybackSettingsUpdateRequest):
    """Update master timeline playback settings."""
    mgr = get_camera_manager()
    status = mgr.controller.update_settings(
        sync_mode=req.sync_mode,
        playback_state=req.playback_state,
        playback_speed=req.playback_speed,
        loop_scenario=req.loop_scenario,
        seek_time_s=req.seek_time_s,
    )
    mgr.save_configuration()
    return {
        "status": "ok",
        "playback": status,
    }


class DemoFallbackUpdateRequest(BaseModel):
    enabled: Optional[bool] = Field(None, description="Enable or disable synthetic fallback plates")
    fallback_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fallback rate fraction (0.0 to 1.0)")
    min_track_frames: Optional[int] = Field(None, ge=1, description="Minimum track lifetime frames before fallback")
    default_state: Optional[str] = Field(None, description="Default 2-letter state code e.g. TN")


@router.get("/anpr/demo-fallback")
def get_anpr_demo_fallback():
    """Retrieve current runtime configuration for controlled demo fallback plates."""
    from app.modules.perception.demo_fallback import get_fallback_config
    cfg = get_fallback_config()
    return {
        "status": "ok",
        "config": cfg.to_dict(),
        "warning": "Generated plates are visual estimates and are strictly excluded from database persistence, verified evidence, and enforcement actions."
    }


@router.put("/anpr/demo-fallback")
def update_anpr_demo_fallback(req: DemoFallbackUpdateRequest):
    """Update runtime configuration for controlled demo fallback plates."""
    from app.modules.perception.demo_fallback import update_fallback_config
    updated = update_fallback_config(
        enabled=req.enabled,
        fallback_rate=req.fallback_rate,
        min_track_frames=req.min_track_frames,
        default_state=req.default_state,
    )
    return {
        "status": "ok",
        "config": updated.to_dict(),
        "warning": "Generated plates are visual estimates and are strictly excluded from database persistence, verified evidence, and enforcement actions."
    }


