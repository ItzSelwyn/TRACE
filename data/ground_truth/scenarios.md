# TRACE M1 Ground-Truth Scenarios

## SCN-001: Normal Four-Camera Trajectory

- Type: normal_trajectory
- Source: CityFlowV2/AICity22 Track 1 MTMC
- Scene: S04
- Split: train
- Source vehicle ID: 260
- Camera sequence: c020 -> c023 -> c029 -> c035

Verified observations:

| Camera | Frame range | Derived time |
|---|---:|---:|
| c020 | 180-246 | 43.805-50.405 seconds |
| c023 | 222-287 | 67.816-74.316 seconds |
| c029 | 85-216 | 134.188-147.288 seconds |
| c035 | 108-174 | 176.268-182.868 seconds |

Expected:

- All observations belong to CityFlow source vehicle ID 260.
- Frame/time progression follows c020 -> c023 -> c029 -> c035.
- The four cameras are distinct camera locations in the S04 network.
- The trajectory is used as the primary TRACE demonstration.
- No plate number is claimed.
- No vehicle type or colour is claimed.
- No exact geographic distance is claimed because individual GPS coordinates are unavailable.