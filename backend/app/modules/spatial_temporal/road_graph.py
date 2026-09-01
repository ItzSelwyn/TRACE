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
    - 'adj': adjacency dict  camera_id → list of neighbour dicts, each with:
        { to_camera_id, edge_id, distance_km, min_travel_time_s,
          max_travel_time_s, speed_limit_kmph }
    - 'cameras': camera metadata dict (camera_id → camera dict)
    - 'edges': raw edge list for lookup
    """
    raw_edges = edges if edges is not None else load_edges()
    cam_data = cameras if cameras is not None else load_cameras()

    adj: dict[str, list[dict[str, Any]]] = {}
    for edge in raw_edges:
        src = edge["from_camera_id"]
        dst = edge["to_camera_id"]
        adj.setdefault(src, []).append({
            "to_camera_id": dst,
            "edge_id": edge["edge_id"],
            "distance_km": float(edge["distance_km"]),
            "min_travel_time_s": int(edge["min_travel_time_s"]),
            "max_travel_time_s": int(edge["max_travel_time_s"]),
            "speed_limit_kmph": int(edge["speed_limit_kmph"]),
        })

    return {"adj": adj, "cameras": cam_data, "edges": raw_edges}


# Module-level singleton — loaded once at import, reused by all requests
_ROAD_GRAPH: dict[str, Any] | None = None


def get_road_graph() -> dict[str, Any]:
    """Return the module-level singleton road graph, loading it on first call."""
    global _ROAD_GRAPH
    if _ROAD_GRAPH is None:
        _ROAD_GRAPH = build_road_graph()
    return _ROAD_GRAPH
