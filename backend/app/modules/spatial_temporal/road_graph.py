"""
Road graph loader for the Spatial-Temporal Reasoning module.

Loads camera nodes and road edges from the seed JSON files and builds an
in-memory adjacency structure ready for reachability checks and shortest-path
computation. No database call is made — this satisfies NFR-08's requirement
that each module layer has a defined interface and can be modified independently.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Seed file locations relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_CAMERAS_PATH = _PROJECT_ROOT / "data" / "seed" / "cameras.json"
_EDGES_PATH = _PROJECT_ROOT / "data" / "seed" / "road_edges.json"


# Fixed UUID-to-camera-alias mapping for CityFlow corridor cameras
CAMERA_ID_ALIASES: dict[str, str] = {
    "c1000000-0000-0000-0000-000000000001": "c020",
    "c2000000-0000-0000-0000-000000000002": "c023",
    "c3000000-0000-0000-0000-000000000003": "c029",
    "c4000000-0000-0000-0000-000000000004": "c035",
}
ALIAS_TO_CANONICAL: dict[str, str] = {v: k for k, v in CAMERA_ID_ALIASES.items()}


def canonical_camera_id(cid: str | None) -> str:
    """Normalize any camera identifier (alias, short code, UUID string) to its canonical graph ID."""
    if not cid:
        return ""
    c = str(cid).strip().lower()
    if c in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[c]
    # Check normalized short codes like '020', 'cam-c020', or 'cam-020'
    for alias, uuid_str in ALIAS_TO_CANONICAL.items():
        if (
            c == alias
            or c == alias.replace("c0", "")
            or c == alias.replace("c", "")
            or c == f"cam-{alias}"
            or c == f"cam-{alias.replace('c', '')}"
        ):
            return uuid_str
    return str(cid).strip()


def load_cameras(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return a dict of camera_id → camera metadata from the seed file."""
    target = path or _CAMERAS_PATH
    if not target.exists():
        return {}
    cameras = json.loads(target.read_text(encoding="utf-8"))
    return {cam["camera_id"]: cam for cam in cameras}


def load_edges(path: Path | None = None) -> list[dict[str, Any]]:
    """Return the raw list of road edge dicts from the seed file."""
    target = path or _EDGES_PATH
    if not target.exists():
        return []
    return json.loads(target.read_text(encoding="utf-8"))


def build_road_graph(
    edges: list[dict[str, Any]] | None = None,
    cameras: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an in-memory road graph from edge and camera data.

    Returns a dict with two keys:
    - 'adj': adjacency dict camera_id → list of neighbour dicts, indexed by both
      canonical UUID and camera alias.
    - 'cameras': camera metadata dict (camera_id → camera dict, with alias entries)
    - 'edges': raw edge list for lookup
    """
    raw_edges = edges if edges is not None else load_edges()
    cam_data = dict(cameras if cameras is not None else load_cameras())

    # Ensure cameras dict also indexes by alias
    for cid, cinfo in list(cam_data.items()):
        alias = CAMERA_ID_ALIASES.get(cid)
        if alias and alias not in cam_data:
            cam_data[alias] = cinfo

    adj: dict[str, list[dict[str, Any]]] = {}
    for edge in raw_edges:
        src = str(edge["from_camera_id"]).strip()
        dst = str(edge["to_camera_id"]).strip()
        entry = {
            "to_camera_id": dst,
            "edge_id": edge["edge_id"],
            "distance_km": float(edge["distance_km"]),
            "min_travel_time_s": int(edge["min_travel_time_s"]),
            "max_travel_time_s": int(edge["max_travel_time_s"]),
            "speed_limit_kmph": int(edge["speed_limit_kmph"]),
        }
        # Index under raw ID
        adj.setdefault(src, []).append(entry)

        # Also index under canonical UUID and alias if distinct
        src_canon = canonical_camera_id(src)
        if src_canon != src:
            adj.setdefault(src_canon, []).append(entry)
        src_alias = CAMERA_ID_ALIASES.get(src_canon)
        if src_alias and src_alias != src:
            adj.setdefault(src_alias, []).append(entry)

    return {"adj": adj, "cameras": cam_data, "edges": raw_edges}


# Module-level singleton — loaded once at import, reused by all requests
_ROAD_GRAPH: dict[str, Any] | None = None


def get_road_graph(reload: bool = False) -> dict[str, Any]:
    """Return the module-level singleton road graph, loading it on first call."""
    global _ROAD_GRAPH
    if _ROAD_GRAPH is None or reload:
        _ROAD_GRAPH = build_road_graph()
    return _ROAD_GRAPH

