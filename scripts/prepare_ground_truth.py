"""Prepare selected CityFlow ground truth for TRACE M1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_COLUMNS = 10
SELECTED_SCENE = "S04"
SELECTED_CAMERAS = ("c020", "c023", "c029", "c035")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def resolve_gt_path(dataset_root: Path, camera_id: str) -> Path:
    candidates = [
        dataset_root / "train" / SELECTED_SCENE / camera_id / "gt" / "gt.txt",
        dataset_root / SELECTED_SCENE / camera_id / "gt" / "gt.txt",
        dataset_root / camera_id / "gt" / "gt.txt",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise SystemExit(
        "Missing ground truth file. Expected one of: "
        + ", ".join(str(path) for path in candidates)
    )


def parse_gt_file(path: Path, dataset_root: Path) -> list[dict]:
    relative_parts = path.relative_to(dataset_root).parts
    if len(relative_parts) >= 4 and relative_parts[0] == "train":
        scene_id = relative_parts[1]
    else:
        scene_id = SELECTED_SCENE

    camera_id = path.parents[1].name
    records = []

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue

        fields = [field.strip() for field in raw_line.split(",")]

        if len(fields) != EXPECTED_COLUMNS:
            raise ValueError(
                f"{path}:{line_number}: expected {EXPECTED_COLUMNS} columns, "
                f"found {len(fields)}"
            )

        try:
            frame_id = int(fields[0])
            vehicle_id = int(fields[1])
            x = float(fields[2])
            y = float(fields[3])
            width = float(fields[4])
            height = float(fields[5])
        except ValueError as error:
            raise ValueError(f"{path}:{line_number}: invalid numeric value") from error

        if frame_id < 1:
            raise ValueError(f"{path}:{line_number}: frame ID must be positive")

        if width <= 0 or height <= 0:
            raise ValueError(f"{path}:{line_number}: bounding-box size must be positive")

        records.append(
            {
                "scene_id": scene_id,
                "camera_id": camera_id,
                "frame_id": frame_id,
                "vehicle_id": vehicle_id,
                "bbox": {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                },
                "source_file": path.relative_to(dataset_root).as_posix(),
            }
        )

    return records


def main() -> int:
    args = parse_args()
    dataset_root = args.dataset_root.resolve()

    if not dataset_root.is_dir():
        raise SystemExit(f"Dataset root does not exist: {dataset_root}")

    all_records = []

    for camera_id in SELECTED_CAMERAS:
        gt_path = resolve_gt_path(dataset_root, camera_id)

        records = parse_gt_file(gt_path, dataset_root)
        all_records.extend(records)
        print(f"{camera_id}: {len(records)} records")

    print(f"Total records: {len(all_records)}")
    print(f"Scene: {SELECTED_SCENE}")
    print(f"Cameras: {', '.join(SELECTED_CAMERAS)}")

    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)

        with args.output.open("w", encoding="utf-8") as output_file:
            for record in all_records:
                output_file.write(json.dumps(record) + "\n")

        print(f"Written: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())