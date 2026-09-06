"""Layer 1 — Perception Module: PostgreSQL/PostGIS Database Persistence for Fused Vehicle Observations and Raw OCR Reads."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Camera, OcrRead, VehicleObservation

logger = logging.getLogger("trace.perception.persistence")

# Deterministic camera alias mapping to seed UUIDs
CAMERA_ALIAS_MAP: Dict[str, uuid.UUID] = {
    "c020": uuid.UUID("c1000000-0000-0000-0000-000000000001"),
    "cam020": uuid.UUID("c1000000-0000-0000-0000-000000000001"),
    "cam-13": uuid.UUID("c1000000-0000-0000-0000-000000000001"),
    "c023": uuid.UUID("c2000000-0000-0000-0000-000000000002"),
    "cam023": uuid.UUID("c2000000-0000-0000-0000-000000000002"),
    "cam-14": uuid.UUID("c2000000-0000-0000-0000-000000000002"),
    "c029": uuid.UUID("c3000000-0000-0000-0000-000000000003"),
    "cam029": uuid.UUID("c3000000-0000-0000-0000-000000000003"),
    "cam-15": uuid.UUID("c3000000-0000-0000-0000-000000000003"),
    "c035": uuid.UUID("c4000000-0000-0000-0000-000000000004"),
    "cam035": uuid.UUID("c4000000-0000-0000-0000-000000000004"),
    "cam-16": uuid.UUID("c4000000-0000-0000-0000-000000000004"),
}

_LAST_DB_ERROR_TIME: float = 0.0
_DB_BACKOFF_SECONDS: float = 10.0


def is_db_in_backoff() -> bool:
    """Check if database operations are currently throttled due to a recent connection failure."""
    global _LAST_DB_ERROR_TIME
    return (time.time() - _LAST_DB_ERROR_TIME) < _DB_BACKOFF_SECONDS


def record_db_error(err_str: str) -> None:
    """Record a DB connection failure and throttle subsequent retry attempts."""
    global _LAST_DB_ERROR_TIME
    now = time.time()
    if (now - _LAST_DB_ERROR_TIME) >= _DB_BACKOFF_SECONDS:
        logger.warning(
            f"[DB WARNING] Database connection offline or failed ({err_str}). "
            f"Perception streams will continue in memory and retry in {_DB_BACKOFF_SECONDS}s."
        )
        _LAST_DB_ERROR_TIME = now


def resolve_camera_uuid(session: Session, camera_identifier: str | uuid.UUID) -> Optional[uuid.UUID]:
    """Resolve camera identifier (string or UUID) to an existing camera_id in PostgreSQL."""
    if isinstance(camera_identifier, uuid.UUID):
        cam = session.get(Camera, camera_identifier)
        return cam.camera_id if cam else None

    clean_id = str(camera_identifier).lower().strip()

    # 1. Try direct alias map
    if clean_id in CAMERA_ALIAS_MAP:
        mapped_uuid = CAMERA_ALIAS_MAP[clean_id]
        if session.get(Camera, mapped_uuid):
            return mapped_uuid

    # 2. Try parsing string as UUID
    try:
        parsed_uuid = uuid.UUID(clean_id)
        if session.get(Camera, parsed_uuid):
            return parsed_uuid
    except ValueError:
        pass

    # 3. Fallback: match by name or return first available camera
    cam_by_name = session.execute(
        select(Camera).where(Camera.name.ilike(f"%{clean_id}%"))
    ).scalars().first()
    if cam_by_name:
        return cam_by_name.camera_id

    first_cam = session.execute(select(Camera)).scalars().first()
    return first_cam.camera_id if first_cam else None


def persist_fused_observation(
    session: Session,
    camera_id_str: str | uuid.UUID,
    track_id: str | int,
    captured_at: Union[datetime, str],
    fused_plate_text: str,
    fused_confidence: Optional[float],
    vehicle_type: str = "car",
    vehicle_colour: str = "white",
    ocr_reads: Optional[List[Dict[str, Any]]] = None,
    appearance_embedding: Optional[List[float]] = None,
) -> Optional[VehicleObservation]:
    """Atomically insert ONE VehicleObservation and its multiple associated OcrRead records into PostgreSQL.
    
    Guarantees:
    - Atomicity: Observation and all OCR reads committed together or rolled back on failure.
    - Graceful degradation: Never crashes caller; throttles retries on DB outages.
    - Real values: Stores actual plate and confidence, or 'NOT READ' / 0.000 for unreadable plates.
    """
    if is_db_in_backoff():
        return None

    try:
        cam_uuid = resolve_camera_uuid(session, camera_id_str)
        if not cam_uuid:
            return None

        # Format captured_at datetime
        if isinstance(captured_at, str):
            try:
                cap_dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            except Exception:
                cap_dt = datetime.now(timezone.utc)
        else:
            cap_dt = captured_at if captured_at.tzinfo else captured_at.replace(tzinfo=timezone.utc)

        # Handle unreadable plate text according to schema constraints
        plate_str = str(fused_plate_text).strip() if fused_plate_text else "NOT READ"
        if not plate_str:
            plate_str = "NOT READ"

        conf_val = round(float(fused_confidence), 3) if fused_confidence is not None else 0.000

        # Validate appearance_embedding if provided
        emb_val = None
        if appearance_embedding is not None and isinstance(appearance_embedding, (list, tuple)):
            if len(appearance_embedding) > 0 and all(np.isfinite(v) for v in appearance_embedding):
                emb_val = [float(v) for v in appearance_embedding]

        # 1. Create VehicleObservation record
        obs_id = uuid.uuid4()
        observation = VehicleObservation(
            observation_id=obs_id,
            camera_id=cam_uuid,
            track_id=str(track_id),
            captured_at=cap_dt,
            fused_plate_text=plate_str,
            fused_confidence=conf_val,
            vehicle_type=str(vehicle_type).lower(),
            vehicle_colour=str(vehicle_colour).lower(),
            appearance_embedding=emb_val,
        )
        session.add(observation)
        session.flush()

        # 2. Create associated OcrRead records
        inserted_reads_count = 0
        if ocr_reads:
            for r in ocr_reads:
                raw_text = str(r.get("raw_text") or r.get("raw_plate_text") or "").strip()
                if not raw_text:
                    continue

                r_conf = round(float(r.get("confidence", 0.0)), 3)
                r_ts_raw = r.get("timestamp") or r.get("frame_timestamp")
                if isinstance(r_ts_raw, str):
                    try:
                        r_dt = datetime.fromisoformat(r_ts_raw.replace("Z", "+00:00"))
                    except Exception:
                        r_dt = cap_dt
                elif isinstance(r_ts_raw, datetime):
                    r_dt = r_ts_raw if r_ts_raw.tzinfo else r_ts_raw.replace(tzinfo=timezone.utc)
                else:
                    r_dt = cap_dt

                ocr_read_record = OcrRead(
                    ocr_read_id=uuid.uuid4(),
                    observation_id=obs_id,
                    frame_timestamp=r_dt,
                    raw_plate_text=raw_text,
                    confidence=r_conf,
                )
                session.add(ocr_read_record)
                inserted_reads_count += 1

        session.commit()
        logger.info(
            f"[DB INSERT] Persisted VehicleObservation {obs_id} (cam={camera_id_str}, track={track_id}, plate='{plate_str}', ocr_reads={inserted_reads_count})"
        )
        return observation

    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        record_db_error(str(e))
        return None
