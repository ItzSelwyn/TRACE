"""
Layer 3 — Spatial-Temporal Reasoning Module
============================================
Implements road-graph reachability, impossible-journey detection, camera-
inconsistency detection, duplicate-plate detection, and full chronological
trajectory reconstruction.

Key formulas (Agent Build Brief §2.2, §2.6):

  implied_speed_kmph = distance_km / (time_gap_s / 3600)
  is_impossible_journey = implied_speed_kmph > speed_limit_kmph * MULTIPLIER
  min_travel_time reachability: time_gap_s < min_travel_time_s → impossible

Anomaly types (must match DB CHECK constraint exactly):
  'impossible_journey' | 'duplicate_plate' | 'camera_inconsistency'
"""
from __future__ import annotations

import heapq
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.modules.spatial_temporal.road_graph import build_road_graph, get_road_graph

# ---------------------------------------------------------------------------
# 1. Shortest path (Dijkstra, weight = min_travel_time_s)
# ---------------------------------------------------------------------------

def shortest_path(
    graph: dict[str, Any],
    from_id: str,
    to_id: str,
) -> tuple[int, list[str]]:
    """Return (min_travel_time_s, path) between two camera nodes.

    Uses Dijkstra over min_travel_time_s weights.  Returns (∞, []) when no
    path exists (disjoint graph or same-node query).

    Parameters
    ----------
    graph: road graph dict returned by build_road_graph()
    from_id, to_id: camera_id strings

    Returns
    -------
    (min_travel_time_s, [from_id, ..., to_id]) — the ordered camera path.
    If from_id == to_id returns (0, [from_id]).
    """
    if from_id == to_id:
        return (0, [from_id])

    adj = graph.get("adj", {})
    dist: dict[str, int] = {from_id: 0}
    prev: dict[str, str | None] = {from_id: None}
    heap: list[tuple[int, str]] = [(0, from_id)]

    while heap:
        cost, node = heapq.heappop(heap)
        if node == to_id:
            break
        if cost > dist.get(node, float("inf")):
            continue
        for neighbour in adj.get(node, []):
            nid = neighbour["to_camera_id"]
            new_cost = cost + neighbour["min_travel_time_s"]
            if new_cost < dist.get(nid, float("inf")):
                dist[nid] = new_cost
                prev[nid] = node
                heapq.heappush(heap, (new_cost, nid))

    if to_id not in dist:
        return (float("inf"), [])  # type: ignore[return-value]

    # Reconstruct path
    path: list[str] = []
    cursor: str | None = to_id
    while cursor is not None:
        path.append(cursor)
        cursor = prev.get(cursor)
    path.reverse()
    return (dist[to_id], path)


# ---------------------------------------------------------------------------
# 2. Direct-edge lookup helpers
# ---------------------------------------------------------------------------

def _direct_edge(graph: dict[str, Any], from_id: str, to_id: str) -> dict[str, Any] | None:
    """Return the direct edge dict from from_id to to_id, or None."""
    for edge in graph.get("adj", {}).get(from_id, []):
        if edge["to_camera_id"] == to_id:
            return edge
    return None


# ---------------------------------------------------------------------------
# 3. Reachability check
# ---------------------------------------------------------------------------

def reachability_check(
    from_id: str,
    to_id: str,
    time_gap_s: float,
    graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check whether a vehicle could plausibly travel from from_id to to_id.

    Returns a dict with:
        reachable (bool): True if time_gap_s ≥ min_travel_time_s on best path
        min_travel_time_s (int): shortest feasible travel time (0 if same node)
        path (list[str]): ordered camera IDs on the shortest path
        time_gap_s (float): the input gap
    """
    g = graph or get_road_graph()
    min_time, path = shortest_path(g, from_id, to_id)

    if min_time == float("inf"):
        # No path in graph — treat as unreachable
        return {
            "reachable": False,
            "min_travel_time_s": None,
            "path": [],
            "time_gap_s": time_gap_s,
        }

    return {
        "reachable": time_gap_s >= min_time,
        "min_travel_time_s": min_time,
        "path": path,
        "time_gap_s": time_gap_s,
    }


# ---------------------------------------------------------------------------
# 4. Implied speed & impossible journey
# ---------------------------------------------------------------------------

def compute_implied_speed(distance_km: float, time_gap_s: float) -> float:
    """Return implied speed in km/h.  Returns 0 if time_gap_s ≤ 0."""
    if time_gap_s <= 0:
        return 0.0
    return round(distance_km / (time_gap_s / 3600.0), 2)


def check_impossible_journey(
    from_id: str,
    to_id: str,
    time_gap_s: float,
    graph: dict[str, Any] | None = None,
    multiplier: float | None = None,
) -> dict[str, Any]:
    """Check whether the implied journey between two cameras is impossible.

    An impossible journey is flagged when either:
    (a) the time_gap_s is less than min_travel_time_s on the best path, OR
    (b) the implied speed exceeds speed_limit × IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER.

    For (b), the speed limit used is from the direct edge if it exists, otherwise
    the slowest (most generous) speed limit along the shortest path.

    Returns a dict with:
        is_impossible_journey (bool)
        reason (str | None): 'too_fast_time' | 'too_fast_speed' | None
        implied_speed_kmph (float | None)
        min_travel_time_s (int | None)
        path (list[str])
    """
    g = graph or get_road_graph()
    mult = multiplier if multiplier is not None else settings.IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER

    reach = reachability_check(from_id, to_id, time_gap_s, g)

    if not reach["reachable"] and reach["min_travel_time_s"] is not None:
        return {
            "is_impossible_journey": True,
            "reason": "too_fast_time",
            "implied_speed_kmph": None,
            "min_travel_time_s": reach["min_travel_time_s"],
            "path": reach["path"],
        }

    if not reach["path"]:
        # No path at all — cannot validate speed, flag as impossible
        return {
            "is_impossible_journey": True,
            "reason": "no_path",
            "implied_speed_kmph": None,
            "min_travel_time_s": None,
            "path": [],
        }

    # Determine distance and speed limit for the direct or shortest route
    direct = _direct_edge(g, from_id, to_id)
    if direct:
        distance_km = direct["distance_km"]
        speed_limit = direct["speed_limit_kmph"]
    else:
        # Sum distances along shortest path edges and use the lowest speed limit
        adj = g.get("adj", {})
        path = reach["path"]
        distance_km = 0.0
        speed_limit = float("inf")
        for i in range(len(path) - 1):
            for edge in adj.get(path[i], []):
                if edge["to_camera_id"] == path[i + 1]:
                    distance_km += edge["distance_km"]
                    speed_limit = min(speed_limit, edge["speed_limit_kmph"])
                    break
        if speed_limit == float("inf"):
            speed_limit = 60  # safe fallback

    if time_gap_s <= 0:
        return {
            "is_impossible_journey": True,
            "reason": "too_fast_time",
            "implied_speed_kmph": None,
            "min_travel_time_s": reach["min_travel_time_s"],
            "path": reach["path"],
        }

    implied = compute_implied_speed(distance_km, time_gap_s)
    ceiling = speed_limit * mult

    return {
        "is_impossible_journey": implied > ceiling,
        "reason": "too_fast_speed" if implied > ceiling else None,
        "implied_speed_kmph": implied,
        "min_travel_time_s": reach["min_travel_time_s"],
        "path": reach["path"],
    }


# ---------------------------------------------------------------------------
# 5. Camera inconsistency detection
# ---------------------------------------------------------------------------

def detect_camera_inconsistency(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag observations whose captured_at moves backward for the same camera+track.

    Groups observations by (camera_id, track_id) and checks chronological order.
    Returns a list of dicts describing each inconsistency:
        { obs_index, camera_id, track_id, captured_at, previous_captured_at }
    """
    from collections import defaultdict

    # Build per-(camera, track) ordered sequences
    groups: dict[tuple[str, str], list[tuple[datetime, int]]] = defaultdict(list)
    for idx, obs in enumerate(observations):
        cam = str(obs.get("camera_id", ""))
        track = str(obs.get("track_id", obs.get("observation_id", idx)))
        ts_raw = obs.get("captured_at")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(str(ts_raw))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        groups[(cam, track)].append((ts, idx))

    inconsistencies: list[dict[str, Any]] = []
    for (cam_id, track_id), entries in groups.items():
        # Sort by insertion order (idx) to detect backward timestamps
        entries.sort(key=lambda x: x[1])
        prev_ts, prev_idx = entries[0]
        for ts, idx in entries[1:]:
            if ts < prev_ts:
                inconsistencies.append({
                    "obs_index": idx,
                    "camera_id": cam_id,
                    "track_id": track_id,
                    "captured_at": ts.isoformat(),
                    "previous_captured_at": prev_ts.isoformat(),
                    "anomaly_type": "camera_inconsistency",
                })
            prev_ts, prev_idx = ts, idx

    return inconsistencies


# ---------------------------------------------------------------------------
# 6. Duplicate plate detection
# ---------------------------------------------------------------------------

def detect_duplicate_plates(
    observations: list[dict[str, Any]],
    graph: dict[str, Any] | None = None,
    overlap_tolerance_s: float = 60.0,
) -> list[dict[str, Any]]:
    """Detect same-plate observations at two cameras that cannot both be true.

    Two observations with the same fused_plate_text are flagged as a
    duplicate_plate anomaly when:
    - They are at different cameras, AND
    - Their timestamps are within overlap_tolerance_s of each other, AND
    - The time gap is less than min_travel_time_s between the two cameras
      (i.e., it's impossible to be at both within that window).

    Returns a list of pair dicts:
        { obs_index_a, obs_index_b, plate_text, camera_a, camera_b,
          time_gap_s, min_travel_time_s, anomaly_type }
    """
    g = graph or get_road_graph()
    duplicates: list[dict[str, Any]] = []

    # Group by plate text
    from collections import defaultdict
    by_plate: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for idx, obs in enumerate(observations):
        plate = str(obs.get("fused_plate_text", "")).strip()
        if plate:
            by_plate[plate].append((idx, obs))

    for plate, entries in by_plate.items():
        n = len(entries)
        for i in range(n):
            for j in range(i + 1, n):
                idx_a, obs_a = entries[i]
                idx_b, obs_b = entries[j]

                cam_a = str(obs_a.get("camera_id", ""))
                cam_b = str(obs_b.get("camera_id", ""))

                if cam_a == cam_b:
                    continue  # same camera — normal re-sighting

                # Parse timestamps
                try:
                    ts_a = datetime.fromisoformat(str(obs_a["captured_at"]))
                    ts_b = datetime.fromisoformat(str(obs_b["captured_at"]))
                    if ts_a.tzinfo is None:
                        ts_a = ts_a.replace(tzinfo=timezone.utc)
                    if ts_b.tzinfo is None:
                        ts_b = ts_b.replace(tzinfo=timezone.utc)
                except (KeyError, ValueError):
                    continue

                time_gap_s = abs((ts_b - ts_a).total_seconds())

                # Only flag if timestamps are close enough to be suspicious
                if time_gap_s > overlap_tolerance_s:
                    continue

                # Check reachability — if not reachable in that time it's a dup
                reach = reachability_check(cam_a, cam_b, time_gap_s, g)
                if not reach["reachable"]:
                    duplicates.append({
                        "obs_index_a": idx_a,
                        "obs_index_b": idx_b,
                        "plate_text": plate,
                        "camera_a": cam_a,
                        "camera_b": cam_b,
                        "time_gap_s": time_gap_s,
                        "min_travel_time_s": reach["min_travel_time_s"],
                        "anomaly_type": "duplicate_plate",
                    })

    return duplicates


# ---------------------------------------------------------------------------
# 7. Full trajectory reconstruction
# ---------------------------------------------------------------------------

def reconstruct_trajectory(
    plate_text: str,
    observations: list[dict[str, Any]],
    graph: dict[str, Any] | None = None,
    multiplier: float | None = None,
) -> dict[str, Any]:
    """Reconstruct a chronological trajectory with full anomaly annotation.

    Takes the raw list of per-camera observations (already identity-scored from
    Layer 2) and:
    1. Sorts them chronologically by captured_at.
    2. For each consecutive pair, checks impossible-journey.
    3. Detects camera-inconsistency across same-camera+track groups.
    4. Detects duplicate plates.
    5. Annotates each observation with is_impossible_journey, anomaly_type,
       implied_speed_kmph.

    Returns:
        {
          plate: str,
          observations: list[dict],   # sorted, annotated
          anomaly_flags: list[str],   # distinct anomaly types present
          total_anomalies: int,
        }
    """
    g = graph or get_road_graph()
    mult = multiplier if multiplier is not None else settings.IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER

    if not observations:
        return {
            "plate": plate_text,
            "observations": [],
            "anomaly_flags": [],
            "total_anomalies": 0,
        }

    # --- Camera inconsistency (detected on input sequence order) -----------
    inconsistencies = detect_camera_inconsistency(observations)
    incon_keys = {(e["camera_id"], e["track_id"], e["captured_at"]) for e in inconsistencies}

    # --- Sort by captured_at for trajectory reasoning ----------------------
    def _parse_ts(obs: dict[str, Any]) -> datetime:
        raw = obs.get("captured_at", "")
        try:
            ts = datetime.fromisoformat(str(raw))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    sorted_obs = sorted(observations, key=_parse_ts)

    # --- Duplicate plates --------------------------------------------------
    duplicates = detect_duplicate_plates(sorted_obs, g)
    dup_indices: set[int] = set()
    for d in duplicates:
        dup_indices.add(d["obs_index_a"])
        dup_indices.add(d["obs_index_b"])

    # --- Impossible journey (consecutive pairs) ----------------------------
    impossible_indices: dict[int, dict[str, Any]] = {}
    for i in range(len(sorted_obs) - 1):
        obs_a = sorted_obs[i]
        obs_b = sorted_obs[i + 1]

        cam_a = str(obs_a.get("camera_id", ""))
        cam_b = str(obs_b.get("camera_id", ""))

        if cam_a == cam_b:
            continue  # same camera consecutive sightings — not a journey

        try:
            ts_a = _parse_ts(obs_a)
            ts_b = _parse_ts(obs_b)
            time_gap_s = (ts_b - ts_a).total_seconds()
        except Exception:
            continue

        ij = check_impossible_journey(cam_a, cam_b, time_gap_s, g, mult)
        if ij["is_impossible_journey"]:
            # Annotate the *later* observation (obs_b at index i+1)
            impossible_indices[i + 1] = ij

    # --- Build annotated output -------------------------------------------
    anomaly_types_seen: set[str] = set()
    annotated: list[dict[str, Any]] = []

    for idx, obs in enumerate(sorted_obs):
        annotated_obs = dict(obs)
        cam = str(obs.get("camera_id", ""))
        track = str(obs.get("track_id", obs.get("observation_id", idx)))
        ts_val = str(obs.get("captured_at", ""))

        # Default: no anomaly
        annotated_obs.setdefault("is_impossible_journey", False)
        annotated_obs.setdefault("anomaly_type", None)
        annotated_obs.setdefault("implied_speed_kmph", None)

        if idx in impossible_indices:
            ij_info = impossible_indices[idx]
            annotated_obs["is_impossible_journey"] = True
            annotated_obs["anomaly_type"] = "impossible_journey"
            annotated_obs["implied_speed_kmph"] = ij_info.get("implied_speed_kmph")
            annotated_obs["match_confidence_label"] = "candidate"  # demote confidence
            anomaly_types_seen.add("impossible_journey")

        if idx in dup_indices and not annotated_obs["is_impossible_journey"]:
            annotated_obs["anomaly_type"] = "duplicate_plate"
            anomaly_types_seen.add("duplicate_plate")

        if (cam, track, ts_val) in incon_keys:
            annotated_obs["anomaly_type"] = "camera_inconsistency"
            anomaly_types_seen.add("camera_inconsistency")

        annotated.append(annotated_obs)

    return {
        "plate": plate_text,
        "observations": annotated,
        "anomaly_flags": sorted(anomaly_types_seen),
        "total_anomalies": len(impossible_indices) + len(duplicates) + len(inconsistencies),
    }
