from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_prepare_ground_truth_supports_flattened_layout(tmp_path: Path):
    dataset_root = tmp_path / "CityFlow"
    for camera in ("c020", "c023", "c029", "c035"):
        gt_dir = dataset_root / camera / "gt"
        gt_dir.mkdir(parents=True)
        gt_file = gt_dir / "gt.txt"
        gt_file.write_text(
            "1,260,10,20,30,40,1,-1,-1,-1\n"
            "2,260,11,21,31,41,1,-1,-1,-1\n",
            encoding="utf-8",
        )

    output = tmp_path / "converted" / "cityflow_train_gt.jsonl"

    subprocess.run(
        [
            sys.executable,
            "scripts/prepare_ground_truth.py",
            "--dataset-root",
            str(dataset_root),
            "--output",
            str(output),
        ],
        check=True,
    )

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 8
    first = json.loads(lines[0])
    assert first["camera_id"] == "c020"
    assert first["vehicle_id"] == 260
    assert first["source_file"] == "c020/gt/gt.txt"
