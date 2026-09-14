"""Real-Time PostgreSQL Database & ResNet Embedding Live Monitor for TRACE.

Usage:
  python scripts/live_db_monitor.py
  python scripts/live_db_monitor.py --once
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Configure stdout for UTF-8 compatibility
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend directory to path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np
from sqlalchemy import create_engine, text

from app.config import settings


def format_emb(emb_raw, status: str = None, reason: str = None) -> str:
    """Format a 512-dim embedding for concise display."""
    if emb_raw and isinstance(emb_raw, (list, tuple)) and len(emb_raw) == 512:
        first_few = ", ".join(f"{float(v):.3f}" for v in emb_raw[:4])
        l2_norm = float(np.linalg.norm(emb_raw))
        return f"[EMB 512-d] ({first_few}, ...) | L2={l2_norm:.2f}"
    
    if status == "pending":
        return "[PENDING EMBEDDING]"
    if reason:
        return f"[NO EMBEDDING] ({reason})"
    return "[NO EMBEDDING]"


def print_stats_block(conn):
    """Print structured coverage metrics, failure reasons, and camera breakdown."""
    overview_query = text("""
        SELECT 
            COUNT(*) as total_obs,
            COUNT(CASE WHEN embedding_status = 'complete' OR jsonb_typeof(appearance_embedding) = 'array' THEN 1 END) as complete_count,
            COUNT(CASE WHEN embedding_status = 'pending' THEN 1 END) as pending_count,
            COUNT(CASE WHEN embedding_status = 'failed' THEN 1 END) as failed_count,
            COUNT(DISTINCT CASE WHEN fused_plate_text != 'NOT READ' THEN fused_plate_text END) as unique_plates
        FROM vehicle_observations;
    """)
    overview = conn.execute(overview_query).fetchone()

    reasons_query = text("""
        SELECT 
            COALESCE(embedding_failure_reason, 'unspecified') as reason,
            COUNT(*) as count
        FROM vehicle_observations
        WHERE (embedding_status = 'failed' OR appearance_embedding IS NULL)
        GROUP BY embedding_failure_reason
        ORDER BY count DESC;
    """)
    reasons = conn.execute(reasons_query).fetchall()

    camera_query = text("""
        SELECT 
            COALESCE(c.name, SUBSTRING(vo.camera_id::text, 1, 6)) as cam_name,
            COUNT(*) as total,
            COUNT(CASE WHEN vo.embedding_status = 'complete' OR jsonb_typeof(vo.appearance_embedding) = 'array' THEN 1 END) as complete_count
        FROM vehicle_observations vo
        LEFT JOIN cameras c ON vo.camera_id = c.camera_id
        GROUP BY c.name, vo.camera_id
        ORDER BY cam_name;
    """)
    cam_rows = conn.execute(camera_query).fetchall()

    if overview:
        total = overview.total_obs
        comp = overview.complete_count
        pend = overview.pending_count
        fail = overview.failed_count
        cov_pct = (comp / max(1, total)) * 100.0

        print("\n" + "=" * 80)
        print("                 TRACE EMBEDDING COVERAGE & HEALTH METRICS")
        print("=" * 80)
        print(f" Total Records:     {total:,}")
        print(f" Complete (512-d):  {comp:,} ({cov_pct:.1f}%)")
        print(f" Pending:           {pend:,}")
        print(f" Failed:            {fail:,}")
        print(f" Unique Plates:     {overview.unique_plates:,}")
        print("-" * 80)

        print(" Per-Camera Embedding Rates:")
        for r in cam_rows:
            c_pct = (r.complete_count / max(1, r.total)) * 100.0
            print(f"   * {str(r.cam_name):<20} {r.complete_count:,} / {r.total:,} ({c_pct:.1f}%)")

        if reasons:
            print("-" * 80)
            print(" Failure Reasons Breakdown:")
            for r in reasons:
                print(f"   * {r.reason:<35} : {r.count:,}")
        print("=" * 80 + "\n")


def run_live_monitor(interval: float = 1.0, once: bool = False):
    print("=" * 115)
    print("               TRACE PERCEPTION & IDENTITY LAYER -- REAL-TIME DATABASE MONITOR")
    print("=" * 115)
    print(f"Connecting to: {settings.DATABASE_URL_SYNC}")
    
    try:
        engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Connected to PostgreSQL in Docker successfully.\n")
    except Exception as exc:
        print(f"Failed to connect to database: {exc}")
        print("\nMake sure your Docker container is running: `docker ps`")
        return

    if once:
        with engine.connect() as conn:
            print_stats_block(conn)
        return

    print("Streaming live vehicle observations as they are inserted/updated...\n")
    print(f"{'TIME':<8} | {'CAM':<5} | {'TRACK':<8} | {'TYPE':<6} | {'COLOUR':<7} | {'PLATE':<12} | {'CONF':<5} | {'RESNET FEATURE EMBEDDING'}")
    print("-" * 115)

    seen_states: Dict[str, str] = {}
    
    init_query = text("""
        SELECT 
            vo.observation_id,
            COALESCE(c.name, SUBSTRING(vo.camera_id::text, 1, 6)) as cam_name,
            vo.track_id,
            vo.captured_at,
            vo.vehicle_type,
            vo.vehicle_colour,
            vo.fused_plate_text,
            vo.fused_confidence,
            vo.appearance_embedding,
            vo.embedding_status,
            vo.embedding_failure_reason
        FROM vehicle_observations vo
        LEFT JOIN cameras c ON vo.camera_id = c.camera_id
        ORDER BY vo.captured_at DESC
        LIMIT 6;
    """)

    with engine.connect() as conn:
        rows = conn.execute(init_query).fetchall()
        for row in reversed(rows):
            oid = str(row.observation_id)
            seen_states[oid] = str(row.embedding_status)
            t_str = row.captured_at.strftime("%H:%M:%S") if row.captured_at else "--:--:--"
            emb_str = format_emb(row.appearance_embedding, row.embedding_status, row.embedding_failure_reason)
            plate_display = row.fused_plate_text if row.fused_plate_text != "NOT READ" else "--"
            conf_str = f"{float(row.fused_confidence)*100:.0f}%" if row.fused_confidence else "0%"
            print(f"{t_str:<8} | {str(row.cam_name):<5} | {str(row.track_id):<8} | {str(row.vehicle_type):<6} | {str(row.vehicle_colour):<7} | {plate_display:<12} | {conf_str:<5} | {emb_str}", flush=True)

    poll_query = text("""
        SELECT 
            vo.observation_id,
            COALESCE(c.name, SUBSTRING(vo.camera_id::text, 1, 6)) as cam_name,
            vo.track_id,
            vo.captured_at,
            vo.vehicle_type,
            vo.vehicle_colour,
            vo.fused_plate_text,
            vo.fused_confidence,
            vo.appearance_embedding,
            vo.embedding_status,
            vo.embedding_failure_reason
        FROM vehicle_observations vo
        LEFT JOIN cameras c ON vo.camera_id = c.camera_id
        ORDER BY vo.captured_at DESC
        LIMIT 25;
    """)

    tick = 0
    try:
        while True:
            time.sleep(interval)
            tick += 1
            with engine.connect() as conn:
                rows = conn.execute(poll_query).fetchall()
                for row in reversed(rows):
                    oid = str(row.observation_id)
                    curr_status = str(row.embedding_status)
                    prev_status = seen_states.get(oid)

                    is_new = prev_status is None
                    is_upgrade = prev_status == "pending" and curr_status == "complete"

                    if is_new or is_upgrade:
                        seen_states[oid] = curr_status
                        t_str = row.captured_at.strftime("%H:%M:%S") if row.captured_at else "--:--:--"
                        emb_str = format_emb(row.appearance_embedding, row.embedding_status, row.embedding_failure_reason)
                        if is_upgrade:
                            emb_str = f"[UPGRADED 512-d] {emb_str.replace('[EMB 512-d] ', '')}"
                        plate_display = row.fused_plate_text if row.fused_plate_text != "NOT READ" else "--"
                        conf_str = f"{float(row.fused_confidence)*100:.0f}%" if row.fused_confidence else "0%"
                        print(f"{t_str:<8} | {str(row.cam_name):<5} | {str(row.track_id):<8} | {str(row.vehicle_type):<6} | {str(row.vehicle_colour):<7} | {plate_display:<12} | {conf_str:<5} | {emb_str}", flush=True)

                if tick % 15 == 0:
                    print_stats_block(conn)
    except KeyboardInterrupt:
        print("\nLive monitor stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live DB Monitor")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Print stats summary once and exit")
    args = parser.parse_args()

    run_live_monitor(interval=args.interval, once=args.once)
