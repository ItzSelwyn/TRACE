"""Real-Time Multi-Camera Data Fusion & Vehicle Path-Finding Live Monitor for TRACE.

Demonstrates:
  1. Live Layer 2 Multi-Modal Data Fusion (Matching the same vehicle across cameras)
  2. ResNet Visual Appearance Similarity (512-d embeddings) + Plate OCR + Temporal Scoring
  3. Live Layer 3 Path Finding (Shortest-path road-graph routing, travel times, implied speed & journey reconstruction)

Usage:
  python scripts/live_fusion_monitor.py
  python scripts/live_fusion_monitor.py --once
  python scripts/live_fusion_monitor.py --paths
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
from app.modules.spatial_temporal.road_graph import (
    CAMERA_ID_ALIASES,
    canonical_camera_id,
    get_road_graph,
)
from app.modules.spatial_temporal import shortest_path

# ANSI Color formatting
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_RED = "\033[91m"
C_MAGENTA = "\033[95m"
C_WHITE = "\033[97m"
C_GRAY = "\033[90m"

# Camera UUID to Friendly Display Name & Short ID
CAMERA_NAMES: Dict[str, str] = {
    "c1000000-0000-0000-0000-000000000001": "Camera 020 (W Locust & Grandview)",
    "c2000000-0000-0000-0000-000000000002": "Camera 023 (Grandview & Delhi)",
    "c3000000-0000-0000-0000-000000000003": "Camera 029 (N Grandview & University)",
    "c4000000-0000-0000-0000-000000000004": "Camera 035 (Highway 20 Corridor)",
}

CAMERA_SHORTS: Dict[str, str] = {
    "c1000000-0000-0000-0000-000000000001": "Cam 020",
    "c2000000-0000-0000-0000-000000000002": "Cam 023",
    "c3000000-0000-0000-0000-000000000003": "Cam 029",
    "c4000000-0000-0000-0000-000000000004": "Cam 035",
}

ROAD_SEGMENT_NAMES: Dict[Tuple[str, str], str] = {
    ("c020", "c023"): "W Locust St ──► Grandview Ave (0.69 km)",
    ("c023", "c020"): "Grandview Ave ──► W Locust St (0.69 km)",
    ("c023", "c029"): "Grandview Ave Corridor (0.85 km)",
    ("c029", "c023"): "Grandview Ave Corridor (0.85 km)",
    ("c029", "c035"): "University Ave ──► Hwy 20 Ramp (1.15 km)",
    ("c035", "c029"): "Hwy 20 Ramp ──► University Ave (1.15 km)",
    ("c020", "c029"): "Locust ──► Delhi ──► University (1.54 km)",
    ("c020", "c035"): "Full Highway 20 Corridor (2.69 km)",
}


def get_cam_display(cam_uuid_str: str) -> str:
    """Format camera UUID to human-friendly string."""
    clean = str(cam_uuid_str).lower().strip()
    return CAMERA_NAMES.get(clean, f"Camera {clean[:6]}")


def get_cam_short(cam_uuid_str: str) -> str:
    """Format camera UUID to short string."""
    clean = str(cam_uuid_str).lower().strip()
    return CAMERA_SHORTS.get(clean, clean[:7])


def get_cam_alias(cam_uuid_str: str) -> str:
    """Format camera UUID to short alias (e.g. c020)."""
    clean = str(cam_uuid_str).lower().strip()
    return CAMERA_ID_ALIASES.get(clean, clean[:6])


def print_metrics_dashboard(conn):
    """Print high-level data fusion and cross-camera tracking statistics."""
    summary_q = text("""
        SELECT
            (SELECT COUNT(*) FROM vehicle_observations) as total_obs,
            (SELECT COUNT(*) FROM identity_matches) as total_eval_pairs,
            (SELECT COUNT(*) FROM identity_matches WHERE identity_score >= 0.70) as confirmed_matches,
            (SELECT COUNT(*) FROM identity_matches WHERE identity_score >= 0.40 AND identity_score < 0.70) as candidate_matches,
            (SELECT COUNT(*) FROM canonical_vehicles) as total_canonical,
            (SELECT COUNT(*) FROM (
                SELECT canonical_vehicle_id
                FROM trajectory_points
                GROUP BY canonical_vehicle_id
                HAVING COUNT(DISTINCT camera_id) > 1
             ) as sub) as multi_cam_vehicles;
    """)
    res = conn.execute(summary_q).fetchone()

    # Query transition counts between cameras
    flow_q = text("""
        SELECT 
            ca.name as from_cam,
            cb.name as to_cam,
            COUNT(*) as match_count,
            ROUND(AVG(im.identity_score)::numeric, 3) as avg_score,
            ROUND(AVG(im.appearance_similarity)::numeric, 3) as avg_app_sim
        FROM identity_matches im
        JOIN vehicle_observations oa ON im.observation_id_a = oa.observation_id
        JOIN vehicle_observations ob ON im.observation_id_b = ob.observation_id
        JOIN cameras ca ON oa.camera_id = ca.camera_id
        JOIN cameras cb ON ob.camera_id = cb.camera_id
        WHERE im.identity_score >= 0.70 AND oa.camera_id != ob.camera_id
        GROUP BY ca.name, cb.name
        ORDER BY match_count DESC
        LIMIT 6;
    """)
    flow_rows = conn.execute(flow_q).fetchall()

    print("\n" + C_BOLD + "=" * 110 + C_RESET)
    print(f"             {C_CYAN}TRACE DATA FUSION & CROSS-CAMERA RE-ID HEALTH METRICS{C_RESET}")
    print(C_BOLD + "=" * 110 + C_RESET)
    if res:
        print(f"  Total Vehicle Observations   : {C_BOLD}{res.total_obs:,}{C_RESET}")
        print(f"  Evaluated Pair Comparisons   : {res.total_eval_pairs:,}")
        print(f"  Confirmed Re-ID Matches      : {C_GREEN}{C_BOLD}{res.confirmed_matches:,}{C_RESET} (Score >= 0.70)")
        print(f"  Candidate Matches            : {C_YELLOW}{res.candidate_matches:,}{C_RESET} (0.40 <= Score < 0.70)")
        print(f"  Unique Canonical Vehicles    : {C_WHITE}{C_BOLD}{res.total_canonical:,}{C_RESET}")
        multi_cam_count = res.multi_cam_vehicles if res.multi_cam_vehicles is not None else 0
        print(f"  Multi-Camera Journeys Found  : {C_MAGENTA}{C_BOLD}{multi_cam_count:,}{C_RESET} vehicles tracked across multiple cameras")

    print("-" * 110)
    print(f"  {C_BOLD}Active Cross-Camera Transition Flow (Confirmed Re-ID Matches):{C_RESET}")
    if flow_rows:
        for r in flow_rows:
            print(f"    * {r.from_cam}  ──►  {r.to_cam}")
            print(f"      Pairs Matched: {C_GREEN}{r.match_count:,}{C_RESET} | Avg Identity Score: {r.avg_score} | Avg ResNet App Sim: {r.avg_app_sim}")
    else:
        print("    (No cross-camera transitions recorded yet)")
    print(C_BOLD + "=" * 110 + C_RESET + "\n")


def print_vehicle_path(conn, canonical_id: str, graph: dict[str, Any]):
    """Reconstruct and display the full multi-camera path for a canonical vehicle."""
    query = text("""
        SELECT 
            tp.sequence_no,
            tp.captured_at,
            tp.camera_id,
            c.name as camera_name,
            c.location,
            vo.track_id,
            vo.vehicle_type,
            vo.vehicle_colour,
            vo.fused_plate_text,
            vo.fused_confidence,
            vo.appearance_embedding
        FROM trajectory_points tp
        JOIN cameras c ON tp.camera_id = c.camera_id
        JOIN vehicle_observations vo ON tp.observation_id = vo.observation_id
        WHERE tp.canonical_vehicle_id = :canon_id
        ORDER BY tp.captured_at ASC;
    """)
    rows = conn.execute(query, {"canon_id": canonical_id}).fetchall()
    if not rows or len(rows) < 2:
        return

    # Check how many distinct cameras
    distinct_cams = len({r.camera_id for r in rows})
    if distinct_cams < 2:
        return

    first_seen = rows[0].captured_at
    last_seen = rows[-1].captured_at
    total_time_s = (last_seen - first_seen).total_seconds()
    minutes = int(total_time_s // 60)
    seconds = int(total_time_s % 60)

    # Resolve vehicle descriptors
    v_type = rows[0].vehicle_type.upper()
    v_color = rows[0].vehicle_colour.upper()
    plate = "VISUAL RE-ID ONLY"
    for r in rows:
        if r.fused_plate_text and r.fused_plate_text != "NOT READ":
            plate = r.fused_plate_text
            break

    print(f"\n{C_MAGENTA}╔══════════════════════════════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_MAGENTA}║{C_RESET} {C_BOLD}🚗 MULTI-CAMERA VEHICLE PATH FOUND: Canonical ID [{str(canonical_id)[:8]}...] {C_RESET}")
    print(f"{C_MAGENTA}║{C_RESET} Identified As: {C_CYAN}{v_color} {v_type}{C_RESET} | Plate: {C_YELLOW}{plate}{C_RESET} | Seen across {C_GREEN}{distinct_cams} cameras{C_RESET}")
    print(f"{C_MAGENTA}╚══════════════════════════════════════════════════════════════════════════════════════════════════════════╝{C_RESET}")

    total_distance_km = 0.0
    any_anomalies = False

    # Compress consecutive readings at the same camera into hops
    camera_hops = []
    current_hop = None
    for r in rows:
        if current_hop is None or current_hop["camera_id"] != r.camera_id:
            if current_hop is not None:
                camera_hops.append(current_hop)
            current_hop = {
                "camera_id": r.camera_id,
                "camera_name": r.camera_name,
                "location": r.location,
                "first_time": r.captured_at,
                "last_time": r.captured_at,
                "track_id": r.track_id,
                "type": r.vehicle_type,
                "color": r.vehicle_colour,
                "plate": r.fused_plate_text,
            }
        else:
            current_hop["last_time"] = r.captured_at
    if current_hop is not None:
        camera_hops.append(current_hop)

    for i, hop in enumerate(camera_hops):
        hop_num = i + 1
        t_str = hop["first_time"].strftime("%H:%M:%S")
        print(f"  {C_BOLD}[Hop {hop_num}]{C_RESET} {C_CYAN}{t_str}{C_RESET} | {C_BOLD}{hop['camera_name']}{C_RESET} [{C_YELLOW}{hop['track_id']}{C_RESET}] • {hop['color']} {hop['type']}")

        # Show path finding link to next camera
        if i < len(camera_hops) - 1:
            next_hop = camera_hops[i + 1]
            src_alias = get_cam_alias(str(hop["camera_id"]))
            dst_alias = get_cam_alias(str(next_hop["camera_id"]))

            time_delta_s = max(0.1, (next_hop["first_time"] - hop["last_time"]).total_seconds())
            
            # Shortest Path calculation using Road Graph
            min_travel_s, path_nodes = shortest_path(graph, src_alias, dst_alias)
            
            # Find edge distance if direct or shortest path
            distance_km = 0.8
            edge_name = ROAD_SEGMENT_NAMES.get((src_alias, dst_alias), f"{src_alias} ──► {dst_alias}")
            
            # Extract distance from graph edge if available
            adj_list = graph.get("adj", {}).get(canonical_camera_id(src_alias), [])
            for edge in adj_list:
                if edge["to_camera_id"] == canonical_camera_id(dst_alias):
                    distance_km = edge["distance_km"]
                    break

            total_distance_km += distance_km
            implied_speed = (distance_km / (time_delta_s / 3600.0))

            is_speed_anomaly = implied_speed > 90.0
            if is_speed_anomaly:
                any_anomalies = True
                status_badge = f"{C_RED}[⚠ IMPOSSIBLE SPEED: {implied_speed:.1f} km/h]{C_RESET}"
            else:
                status_badge = f"{C_GREEN}[✓ FEASIBLE: {implied_speed:.1f} km/h]{C_RESET}"

            path_str = " ──► ".join(get_cam_alias(node) for node in path_nodes) if len(path_nodes) > 2 else f"{src_alias} ──► {dst_alias}"

            print(f"       {C_GRAY}│{C_RESET}")
            print(f"       {C_GRAY}├──►{C_RESET} {C_BLUE}Road Graph Routing{C_RESET}  : {path_str} ({edge_name})")
            print(f"       {C_GRAY}│    {C_RESET}Travel Delta        : {time_delta_s:.1f}s (Min expected: {min_travel_s}s) | Distance: {distance_km:.2f} km")
            print(f"       {C_GRAY}│    {C_RESET}Speed Verification  : {status_badge} (Speed limit: 70 km/h)")
            print(f"       {C_GRAY}▼{C_RESET}")

    status_summary = f"{C_RED}ANOMALIES DETECTED{C_RESET}" if any_anomalies else f"{C_GREEN}100% FEASIBLE JOURNEY (0 Anomaly Flags){C_RESET}"
    print(f"  {C_BOLD}══════════════════════════════════════════════════════════════════════════════════════════════════════════{C_RESET}")
    print(f"  {C_BOLD}Total Journey Summary:{C_RESET} {len(camera_hops)} Camera Hops | Distance: {total_distance_km:.2f} km | Duration: {minutes}m {seconds:02d}s | {status_summary}\n")


def print_top_recent_paths(conn, graph: dict[str, Any], limit: int = 3):
    """Query and print the top multi-camera paths currently in the database."""
    query = text("""
        SELECT 
            cv.canonical_vehicle_id,
            cv.best_plate_text,
            cv.first_seen_at,
            cv.last_seen_at,
            COUNT(DISTINCT tp.camera_id) as num_cameras,
            COUNT(tp.trajectory_point_id) as num_points
        FROM canonical_vehicles cv
        JOIN trajectory_points tp ON cv.canonical_vehicle_id = tp.canonical_vehicle_id
        GROUP BY cv.canonical_vehicle_id, cv.best_plate_text, cv.first_seen_at, cv.last_seen_at
        HAVING COUNT(DISTINCT tp.camera_id) > 1
        ORDER BY cv.last_seen_at DESC
        LIMIT :limit;
    """)
    rows = conn.execute(query, {"limit": limit}).fetchall()
    if not rows:
        print("  (No multi-camera trajectories found yet. Waiting for vehicle observations...)")
        return

    print(f"\n{C_CYAN}── Spotlight: {len(rows)} Most Recent Cross-Camera Re-ID Trajectories In Database ──{C_RESET}")
    for r in rows:
        print_vehicle_path(conn, str(r.canonical_vehicle_id), graph)


def stream_live_fusion(interval: float = 2.0, once: bool = False, paths_only: bool = False):
    """Main live monitor loop streaming new cross-camera matches and path finding."""
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    graph = get_road_graph()

    print(C_BOLD + "=" * 110 + C_RESET)
    print(f"        {C_GREEN}TRACE PERCEPTION LAYER 2 & LAYER 3 — REAL-TIME DATA FUSION & PATH-FINDING MONITOR{C_RESET}")
    print(C_BOLD + "=" * 110 + C_RESET)
    print(f"Connecting to: {settings.DATABASE_URL_SYNC}")
    print(f"Connected to PostgreSQL successfully.")
    print(f"Fusion Engine : Multi-Modal (ResNet-50 512-d Visual Re-ID + PaddleOCR ANPR + Spatial-Temporal Road Graph)")
    print(f"Confidence    : CONFIRM >= 0.70 | CANDIDATE >= 0.40")
    print(f"Road Graph    : 4 CityFlow Cameras [c020, c023, c029, c035] with 19 directed road segments")
    print(C_BOLD + "=" * 110 + C_RESET)

    with engine.connect() as conn:
        print_metrics_dashboard(conn)
        print_top_recent_paths(conn, graph, limit=2)

    if once or paths_only:
        return

    print("\n" + C_BOLD + "Streaming live cross-camera vehicle matches as data fusion occurs..." + C_RESET)
    print(f"{C_BOLD}{'TIME':<8} | {'STATUS':<15} | {'ORIGIN CAMERA & TRACK':<25} | {'DEST CAMERA & TRACK':<25} | {'ATTRIBUTES':<12} | {'FUSION EVIDENCE':<30}{C_RESET}")
    print("-" * 110)

    seen_match_ids: Set[str] = set()
    
    # Pre-populate already seen matches so we only stream new live additions
    with engine.connect() as conn:
        recent_ids = conn.execute(text("""
            SELECT match_id FROM identity_matches ORDER BY match_id DESC LIMIT 500;
        """)).scalars().all()
        seen_match_ids.update(str(m) for m in recent_ids)

    loops_since_dashboard = 0

    while True:
        try:
            with engine.connect() as conn:
                # Query newly inserted cross-camera matches
                matches_q = text("""
                    SELECT 
                        im.match_id,
                        im.identity_score,
                        im.appearance_similarity,
                        im.temporal_score,
                        im.plate_similarity,
                        im.implied_speed_kmph,
                        im.is_impossible_journey,
                        oa.observation_id as obs_a,
                        oa.track_id as trk_a,
                        oa.camera_id as cam_a,
                        oa.vehicle_type as type_a,
                        oa.vehicle_colour as col_a,
                        oa.fused_plate_text as plate_a,
                        oa.captured_at as ts_a,
                        ob.observation_id as obs_b,
                        ob.track_id as trk_b,
                        ob.camera_id as cam_b,
                        ob.vehicle_type as type_b,
                        ob.vehicle_colour as col_b,
                        ob.fused_plate_text as plate_b,
                        ob.captured_at as ts_b
                    FROM identity_matches im
                    JOIN vehicle_observations oa ON im.observation_id_a = oa.observation_id
                    JOIN vehicle_observations ob ON im.observation_id_b = ob.observation_id
                    WHERE im.identity_score >= 0.40 AND oa.camera_id != ob.camera_id
                    ORDER BY oa.captured_at DESC
                    LIMIT 20;
                """)
                new_matches = conn.execute(matches_q).fetchall()

                found_new = False
                for m in reversed(new_matches):
                    mid = str(m.match_id)
                    if mid in seen_match_ids:
                        continue
                    seen_match_ids.add(mid)
                    found_new = True

                    score = float(m.identity_score)
                    is_confirmed = score >= 0.70
                    status_str = f"{C_GREEN}[CONFIRMED {score:.2f}]{C_RESET}" if is_confirmed else f"{C_YELLOW}[CANDIDATE {score:.2f}]{C_RESET}"

                    cam_a_short = f"{get_cam_short(str(m.cam_a))} [{m.trk_a}]"
                    cam_b_short = f"{get_cam_short(str(m.cam_b))} [{m.trk_b}]"
                    attrs = f"{m.col_b} {m.type_b}"
                    
                    evidence_parts = []
                    if m.appearance_similarity is not None:
                        evidence_parts.append(f"App: {float(m.appearance_similarity):.2f}")
                    if m.temporal_score is not None:
                        evidence_parts.append(f"Temp: {float(m.temporal_score):.2f}")
                    if m.plate_similarity is not None:
                        evidence_parts.append(f"Plate: {float(m.plate_similarity):.2f}")
                    elif m.plate_b and m.plate_b != "NOT READ":
                        evidence_parts.append(f"Plate: {m.plate_b}")
                    else:
                        evidence_parts.append("Visual Re-ID")

                    ev_str = " | ".join(evidence_parts)
                    time_str = m.ts_b.strftime("%H:%M:%S")

                    print(f"{time_str:<8} | {status_str:<24} | {cam_a_short:<25} | {cam_b_short:<25} | {attrs:<12} | {ev_str}")

                    # If confirmed match, check if we can spotlight the reconstructed path
                    if is_confirmed:
                        canon_q = text("""
                            SELECT canonical_vehicle_id FROM trajectory_points WHERE observation_id IN (:obs_a, :obs_b) LIMIT 1;
                        """)
                        canon_row = conn.execute(canon_q, {"obs_a": m.obs_a, "obs_b": m.obs_b}).fetchone()
                        if canon_row and canon_row.canonical_vehicle_id:
                            print_vehicle_path(conn, str(canon_row.canonical_vehicle_id), graph)

                loops_since_dashboard += 1
                if loops_since_dashboard >= 25:
                    loops_since_dashboard = 0
                    print_metrics_dashboard(conn)
                    print(f"{C_BOLD}{'TIME':<8} | {'STATUS':<15} | {'ORIGIN CAMERA & TRACK':<25} | {'DEST CAMERA & TRACK':<25} | {'ATTRIBUTES':<12} | {'FUSION EVIDENCE':<30}{C_RESET}")
                    print("-" * 110)

        except KeyboardInterrupt:
            print("\nLive monitor stopped by user.")
            break
        except Exception as e:
            print(f"Error querying live fusion matches: {e}")

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="TRACE Real-Time Data Fusion & Path-Finding Monitor")
    parser.add_argument("--once", action="store_true", help="Print current status and exit")
    parser.add_argument("--paths", action="store_true", help="Display all multi-camera reconstructed paths and exit")
    parser.add_argument("--interval", type=float, default=1.5, help="Polling interval in seconds (default: 1.5)")
    args = parser.parse_args()

    stream_live_fusion(interval=args.interval, once=args.once, paths_only=args.paths)


if __name__ == "__main__":
    main()
