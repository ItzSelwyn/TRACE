"""Validate normalized TRACE ground-truth JSON Lines."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CAMERA_PATTERN = re.compile(r"^c\d+$")
REQUIRED_FIELDS = {
    "scene_id",
    "camera_id",
    "frame_id",
    "vehicle_id",
    "bbox",
    "source_file",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input file does not exist: {args.input}")

    records = []
    errors = []

    for line_number, line in enumerate(
        args.input.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"Line {line_number}: invalid JSON: {error}")
            continue

        missing = REQUIRED_FIELDS - record.keys()
        if missing:
            errors.append(f"Line {line_number}: missing fields {sorted(missing)}")
            continue

        if not record["scene_id"]:
            errors.append(f"Line {line_number}: empty scene_id")

        if not CAMERA_PATTERN.match(record["camera_id"]):
            errors.append(f"Line {line_number}: invalid camera_id")

        if not isinstance(record["frame_id"], int) or record["frame_id"] < 1:
            errors.append(f"Line {line_number}: invalid frame_id")

        bbox = record["bbox"]
        for field in ("x", "y", "width", "height"):
            if field not in bbox or not isinstance(bbox[field], (int, float)):
                errors.append(f"Line {line_number}: invalid bbox.{field}")

        if bbox.get("width", 0) <= 0 or bbox.get("height", 0) <= 0:
            errors.append(f"Line {line_number}: bbox dimensions must be positive")

        if not record["source_file"]:
            errors.append(f"Line {line_number}: empty source_file")

        records.append(record)

    if not records:
        errors.append("No records found")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    scenes = {record["scene_id"] for record in records}
    cameras = {record["camera_id"] for record in records}
    vehicles = {record["vehicle_id"] for record in records}

    print("Validation passed")
    print(f"Records: {len(records)}")
    print(f"Scenes: {sorted(scenes)}")
    print(f"Cameras: {sorted(cameras)}")
    print(f"Vehicles: {len(vehicles)}")
    print(f"Vehicle 260 records: {sum(r['vehicle_id'] == 260 for r in records)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())