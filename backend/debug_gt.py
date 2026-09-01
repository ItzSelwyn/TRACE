#!/usr/bin/env python
"""Debug GT loading."""
from pathlib import Path
from app.modules.perception import load_ground_truth_by_camera, process_all_cameras

# Use the same path calculation as perception.py
DATASET_PATH = Path(__file__).resolve().parents[1] / 'data' / 'ground_truth' / 'cityflow_train_gt.jsonl'
print(f'DATASET_PATH: {DATASET_PATH}')
print(f'Exists: {DATASET_PATH.exists()}')

if DATASET_PATH.exists():
    records = load_ground_truth_by_camera(DATASET_PATH, camera_ids=['c020', 'c023', 'c029', 'c035'])
    print(f'Loaded records by camera: {list(records.keys())}')
    for cam_id, obs in records.items():
        print(f'  {cam_id}: {len(obs)} records')
    
    # Now try processing all cameras
    print('\nProcessing cameras...')
    results = process_all_cameras(['c020', 'c023', 'c029', 'c035'], dataset_records=records)
    for cam_id, result in results.items():
        status = result['camera_status']
        obs_count = len(result['observations'])
        ocr_count = len(result['ocr_reads'])
        print(f'  {cam_id}: status={status}, observations={obs_count}, ocr_reads={ocr_count}')
