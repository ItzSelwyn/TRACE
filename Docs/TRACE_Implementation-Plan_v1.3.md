# TRACE
Tracking, Recognition, Analytics & City-wide Traffic Enforcement

# Implementation Plan — Revised v1.3

Three-person execution team. M1–M6 are retained unchanged. v1.3 adds the P1 UI verification credit to the M2 NFR-05 failure-isolation test so the Implementation Plan matches the TRD sign-off evidence.

## 1. Team Roles — UNCHANGED FROM v1.1

| Role | Ownership |
|---|---|
| P1 — Frontend Developer / UI Engineer | Complete React/TypeScript UI, MapLibre, charts, REST/WebSocket integration. |
| P2 — Backend + ML Engineer | PostgreSQL/PostGIS, FastAPI and all five logical modules plus alerts. |
| P3 — Data Collector & Project Support | Dataset, annotation, ground truth, demo scenarios, QA, documentation support and rehearsal. |

## 2. Six Milestones — RETAINED

| ID | Milestone | End result |
|---|---|---|
| M1 | Foundations | Schema, camera/road data, shared environment and frontend shell. |
| M2 | Perception Layer | Fused observations produced from recorded camera feeds. |
| M3 | Identity Fusion | Identity Score with evidence. |
| M4 | Trajectory Reasoning | Chronological trajectory + impossible journey. |
| M5 | Analytics + Dashboard | Heatmap, OD, segment detail and forecast. |
| M6 | Alerts + Integration + Polish | Live blacklist alert and complete end-to-end demo. |

## 3. M2 — Perception Layer: P2 Failure-Isolation Sign-off
Entry: M1 complete. Exit: FR-PER-01 to FR-PER-05 demonstrable on the seeded dataset AND NFR-05 failure isolation verified.

- P2 integrates YOLO, ByteTrack, PaddleOCR and temporal OCR fusion; writes vehicle_observations and ocr_reads.
- P3 maintains annotations, ground truth and condition-specific evaluation splits and supports OCR testing.
- P1 builds shared Confidence Badge, Status Dot and Map Panel components.
- P2 wraps each camera perception call in its own try/except; failures are logged and skipped for that camera cycle.
- P2 runs each camera ingestion/perception independently as an async task or background job so one camera cannot block others.
- P2 updates cameras.status to degraded or down on feed/perception failure and ensures stale status is not retained.
- P2 applies a per-camera timeout to detection/OCR work.
- P2 ensures exceptions in any module are contained so the FastAPI process and unrelated endpoints remain available.
- P2 + P3 perform the manual failure test: kill/corrupt one simulated camera feed mid-run; confirm other cameras continue and the affected camera appears down in the UI. P1 confirms the affected camera renders correctly on Camera Network Status.
- Record the six-item checklist result as M2 QA evidence before M2 sign-off.

## 4. Other Milestones — UNCHANGED
M3: Identity Fusion; M4: Trajectory Reasoning; M5: Analytics + Dashboard; M6: Alerts + Integration + Polish. Their v1.1 ownership and outcomes remain unchanged.

## 5. Git Workflow — UNCHANGED
- main = stable/demo-ready; dev = shared integration.
- Use short-lived feature branches from dev.
- Pull Requests merge into dev after review; dev merges to main after milestone acceptance.
- Logical TRACE layers remain modules inside the single FastAPI backend; no permanent layer branches are required.

## 6. Definition of Done
The same PRD acceptance criteria remain. M2 additionally requires the NFR-05 failure-isolation checklist to be verified before sign-off.

— TRACE Implementation Plan, Revised v1.3 —
