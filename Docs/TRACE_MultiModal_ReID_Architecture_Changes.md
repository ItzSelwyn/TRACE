# TRACE Architecture & Project Structure Changes
**Document Version:** 1.0  
**Date:** September 6, 2026  
**Scope:** Layer 1 Perception (Appearance Re-ID), Layer 2 Identity Fusion (Multi-Modal), Database Migrations, and Test Suites.

---

## 1. Executive Summary

This document explains the architectural and project structure changes introduced into the TRACE backend to support:
1. **Multi-Modal Identity Fusion (Layer 2)**: Transitioning from a license-plate-dependent scoring formula to a multi-modal fusion architecture supporting both **CityFlowV2 (visual-only, plate-free)** and **ANPR-capable** operational environments.
2. **Vehicle Appearance & Re-ID Pipeline (Layer 1 -> Layer 2)**: Integrating a real vehicle Re-ID neural feature extractor (ResNet34 trained on VeRi-776, plus MobileNetV3 baseline) that derives L2-normalized embeddings from real vehicle bounding-box crops, aggregates multi-frame track representations, and feeds calibrated appearance similarity into Layer 2.
3. **Database Schema Enhancements**: Adding nullable evidence columns to `identity_matches` and `appearance_embedding` (`JSONB`) to `vehicle_observations`, fully backward-compatible via non-destructive Alembic migrations.

---

## 2. Directory Structure Overview

The updated directory tree reflects new modules, models, migrations, and test suites:

```text
TRACE/
├── Docs/
│   └── TRACE_MultiModal_ReID_Architecture_Changes.md   <-- [NEW] This document
│
├── backend/
│   ├── alembic/
│   │   └── versions/
│   │       ├── 20260830_000001_initial_m1_schema.py
│   │       ├── 20260906_000002_multimodal_identity.py          <-- [NEW] Migration 2 (nullable columns + multi-modal signals)
│   │       └── 20260906_000003_vehicle_appearance_embedding.py  <-- [NEW] Migration 3 (appearance_embedding JSONB)
│   │
│   ├── app/
│   │   ├── config.py                                           <-- [MODIFIED] Added multi-modal weights & appearance settings
│   │   ├── db/
│   │   │   └── models.py                                       <-- [MODIFIED] Added appearance_embedding to VehicleObservation, nullable best_plate_text
│   │   │
│   │   ├── modules/
│   │   │   ├── appearance/                                     <-- [NEW PACKAGE] Dedicated Vehicle Appearance / Re-ID
│   │   │   │   ├── __init__.py                                 <-- Public API exports
│   │   │   │   ├── extractor.py                                <-- AppearanceExtractor singleton (single crop & track aggregation)
│   │   │   │   ├── preprocessing.py                            <-- Crop validation, BGR->RGB, resize, ImageNet normalization
│   │   │   │   └── similarity.py                               <-- Cosine similarity & empirical CityFlow calibration
│   │   │   │
│   │   │   ├── identity/                                       <-- [REFACTORED] Layer 2 Identity Fusion
│   │   │   │   ├── __init__.py                                 <-- Updated public exports
│   │   │   │   ├── scoring.py                                  <-- Multi-modal scoring engine with missing-modality guards
│   │   │   │   └── matcher.py                                  <-- Observation pairing, road-graph integration & embedding resolution
│   │   │   │
│   │   │   ├── perception/                                     <-- [MODIFIED] Layer 1 Perception
│   │   │   │   ├── pipeline.py                                 <-- Collects vehicle crops per track, extracts track-level Re-ID
│   │   │   │   └── persistence.py                              <-- Persists appearance_embedding into PostgreSQL
│   │   │   │
│   │   │   └── spatial_temporal/                               <-- Road network graph & travel-time reachability
│   │   │
│   │   └── schemas/
│   │       └── vehicles.py                                     <-- [MODIFIED] Extended EvidenceBreakdown schema
│   │
│   ├── models/                                                 <-- [MODELS DIRECTORY] Centralized model weights
│   │   ├── yolov8n.pt                                          <-- [RELOCATED] YOLOv8n object detection model
│   │   └── resnet34_veri776_deploy.pt                          <-- [NEW WEIGHTS] Pretrained VeRi-776 Vehicle Re-ID backbone
│   │
│   ├── scripts/
│   │   └── verify_identity_fusion.py                           <-- [REWRITTEN] 35-check empirical validation script
│   │
│   └── tests/
│       ├── test_appearance_reid.py                             <-- [NEW] 15 unit tests for appearance module & safety guards
│       ├── test_cityflow_reid_end_to_end.py                    <-- [NEW] Real cross-camera video test on CityFlow footage
│       ├── test_identity_fusion_multimodal.py                  <-- [NEW] 14 multi-modal identity fusion tests
│       ├── test_identity_fusion_m3.py                          <-- [UPDATED] Regression test suite
│       └── test_m3_identity_and_trajectory.py                 <-- [UPDATED] Trajectory & formula verification
```

---

## 3. Detailed Component Breakdown

### 3.1. `app/modules/appearance/` (New Package)
Provides a clean, modular visual representation layer without hardcoding model logic into identity matching:

- **`preprocessing.py`**:
  - `validate_crop(crop, min_size=24)`: Rejects `None`, empty arrays, zero-area crops, non-finite values, and crops smaller than 24x24 pixels.
  - Converts BGR to RGB and generates standard normalized PyTorch tensors (256x256 for ResNet, 224x224 for MobileNet).
- **`similarity.py`**:
  - `compute_cosine_similarity(emb_a, emb_b)`: Computes raw cosine similarity dot product in [-1.0, 1.0].
  - `compute_calibrated_similarity(cosine, min_val, max_val)`: Maps raw cosine to identity similarity [0.0, 1.0] via empirical CityFlow bounds:
    `similarity = clamp((cosine - 0.60) / (0.88 - 0.60), 0.0, 1.0)`
  - `compute_appearance_similarity(emb_a, emb_b)`: End-to-end wrapper returning a calibrated [0, 1] float or `None`.
- **`extractor.py`**:
  - `AppearanceExtractor`: Singleton class loaded once and reused across observations.
  - Automatically loads `resnet34_veri776` (512-dim) or falls back to `mobilenet_v3_small` (1024-dim).
  - `extract(crop)`: Produces an L2-normalized 1D feature vector.
  - `extract_track_embedding(crops)`: Evenly samples up to 5 valid vehicle crops across a track, mean-pools the embeddings, and L2-renormalizes the final vector.
- **`__init__.py`**:
  - Exposes `get_appearance_extractor()`, `compute_appearance_similarity()`, and `extract_vehicle_embedding()`.

---

### 3.2. `app/modules/identity/` (Refactored Layer 2 Engine)

- **Automatic Operational Mode Selection**:
  - **ANPR Mode**: Activates when *both* observations have readable license plates. Plate similarity contributes 35% nominal weight.
  - **CityFlowV2 Mode**: Activates when one or both plates are unreadable (`"NOT READ"` / `None`). Plate weight is 0%; visual appearance (55%), temporal consistency (25%), camera transition (15%), colour (3%), and type (2%) govern identity.
- **Proportional Weight Redistribution**:
  - When an optional modality is unavailable (`None`), its weight is redistributed proportionally among available signals rather than penalizing the score with a false zero.
- **Missing-Modality Safety Guard (Requirement 15)**:
  - If *both* license plate and visual appearance are absent (`not has_primary_evidence`), primary weights are **not** redistributed to weak attributes (colour/type). The score is capped below `CANDIDATE_THRESHOLD` (< 0.40), preventing two white cars from being falsely confirmed as identical based only on color/type.
- **Soft Attribute Evidence**:
  - Type mismatch receives a score of `0.4` (not 0.0).
  - Colour mismatch receives a score of `0.3` (not 0.0).
  - Mismatched attributes reduce confidence softly without causing automatic rejection.
- **Road Graph Integration**:
  - Normalizes short camera aliases (`c020`, `c023`) to canonical road-graph nodes for travel-time reachability and topological transition scoring.
- **Automatic Appearance Resolution in `matcher.py`**:
  - `match_observation_pair` inspects `obs_a.appearance_embedding` and `obs_b.appearance_embedding` and automatically computes `compute_appearance_similarity()`.

---

### 3.3. Database Schema & Migrations

Two non-destructive Alembic migrations were applied:

1. **`alembic/versions/20260906_000002_multimodal_identity.py`**:
   - `identity_matches`: Made `plate_similarity`, `ocr_confidence_component`, `type_match`, and `colour_match` nullable.
   - `identity_matches`: Added `appearance_similarity NUMERIC(4,3) NULL`, `temporal_score NUMERIC(4,3) NULL`, `camera_transition_score NUMERIC(4,3) NULL`.
   - `canonical_vehicles`: Made `best_plate_text` nullable to support plate-free visual clusters.
2. **`alembic/versions/20260906_000003_vehicle_appearance_embedding.py`**:
   - `vehicle_observations`: Added `appearance_embedding JSONB NULL` to store track-level 512-D L2-normalized feature vectors.

ORM model in `app/db/models.py`:
```python
class VehicleObservation(Base):
    # ... existing columns ...
    appearance_embedding: Mapped[Optional[List[float]]] = mapped_column(JSONB, nullable=True)
```

---

### 3.4. Perception & Persistence Integration

- **`app/modules/perception/pipeline.py`**:
  - In `process_frame()`, valid bounding-box crops are added to `trk_info["crops"]` (up to `APPEARANCE_MAX_TRACK_SAMPLES = 5`).
  - In `_persist_track_if_ready()`, when a track finalizes, `extractor.extract_track_embedding()` aggregates the crops into a single L2-normalized embedding and frees memory.
- **`app/modules/perception/persistence.py`**:
  - `persist_fused_observation()` accepts `appearance_embedding` and persists it directly with the observation.

---

### 3.5. Configuration (`app/config.py`)

New named settings were added to `Settings`:

```python
# Multi-modal identity fusion weights (CityFlowV2 / Visual-only)
IDENTITY_APPEARANCE_WEIGHT: float = 0.55
IDENTITY_TEMPORAL_WEIGHT: float = 0.25
IDENTITY_CAMERA_TRANSITION_WEIGHT: float = 0.15
IDENTITY_COLOUR_WEIGHT: float = 0.03
IDENTITY_TYPE_WEIGHT: float = 0.02

# ANPR-capable mode
IDENTITY_PLATE_WEIGHT: float = 0.35
IDENTITY_APPEARANCE_WEIGHT_ANPR: float = 0.30
IDENTITY_TEMPORAL_WEIGHT_ANPR: float = 0.15
IDENTITY_CAMERA_TRANSITION_WEIGHT_ANPR: float = 0.10
IDENTITY_COLOUR_WEIGHT_ANPR: float = 0.05
IDENTITY_TYPE_WEIGHT_ANPR: float = 0.05

# Appearance Re-ID settings
APPEARANCE_REID_ENABLED: bool = True
APPEARANCE_MODEL_NAME: str = "resnet34_veri776"
APPEARANCE_MODEL_PATH: str = "models/resnet34_veri776_deploy.pt"
APPEARANCE_EMBEDDING_DIM: int = 512
APPEARANCE_DEVICE: str = "auto"
APPEARANCE_MIN_CROP_SIZE: int = 24
APPEARANCE_MAX_TRACK_SAMPLES: int = 5
APPEARANCE_COSINE_MIN: float = 0.60
APPEARANCE_COSINE_MAX: float = 0.88

# Perception Detection model
YOLO_MODEL_PATH: str = "models/yolov8n.pt"
```

---

## 4. End-to-End Data Flow

```text
                        CityFlowV2 Video Stream
                                   │
                                   ▼
                       YOLOv8 Detection (BBoxes)
                                   │
                                   ▼
                       ByteTrack (Track IDs)
                                   │
                                   ▼
                 Vehicle Crops (min 24x24 px, BGR->RGB)
                                   │
                                   ▼
                     ResNet34 VeRi-776 Backbone
                                   │
                                   ▼
                     512-D L2-Normalized Vectors
                                   │
                                   ▼
                Track-Level Aggregation (Mean + L2 Norm)
                                   │
                                   ▼
             PostgreSQL: vehicle_observations.appearance_embedding
                                   │
                                   ▼
           match_observation_pair(obs_a, obs_b)
                                   │
                                   ▼
               compute_appearance_similarity(emb_a, emb_b)
               Raw Cosine -> Calibrated Score in [0, 1]
                                   │
                                   ▼
                    compute_identity_score()
      ┌────────────────────────────┴────────────────────────────┐
      ▼                                                         ▼
[ANPR Mode]                                           [CityFlowV2 Mode]
35% Plate + OCR                                       55% Visual Appearance
30% Visual Appearance                                 25% Temporal Plausibility
15% Temporal Plausibility                             15% Camera Transition Topology
10% Camera Transition Topology                         3% Colour Match (Soft)
 5% Colour Match (Soft)                                2% Type Match (Soft)
 5% Type Match (Soft)                                  0% Plate (Ignored)
      └────────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
             Composite Identity Score & Explainability Breakdown
             (CONFIRMED >= 0.70, CANDIDATE >= 0.40, NO_MATCH < 0.40)
                                   │
                                   ▼
                      Canonical Vehicle Clustering
```

---

## 5. Verification & Test Suite Summary

The changes were validated across automated unit tests, empirical video tests, and verification scripts:

| Test Suite | File | Tests Passed | Purpose |
|---|---|---|---|
| **Appearance Unit Tests** | `tests/test_appearance_reid.py` | **15 / 15** | Crop validation, L2 normalization, deterministic output, distinct vehicles, singleton reuse, Layer 2 integration, missing modality safety guard. |
| **CityFlowV2 End-to-End** | `tests/test_cityflow_reid_end_to_end.py` | **2 / 2** | Cross-camera evaluation on real `c020` vs `c023` footage with `plate=None`. |
| **Multi-Modal Identity** | `tests/test_identity_fusion_multimodal.py` | **14 / 14** | Tests A through H (ANPR and visual-only scenarios). |
| **M3 Identity Tests** | `tests/test_identity_fusion_m3.py` | **11 / 11** | Regression tests for plate similarity, OCR reliability, and soft attributes. |
| **Trajectory Tests** | `tests/test_m3_identity_and_trajectory.py` | **42 / 42** | Trajectory building and road-graph integration. |
| **Verification Script** | `scripts/verify_identity_fusion.py` | **35 / 35** | Diagnostic verification covering appearance, CityFlow statistics, and Scenarios A–I. |
| **Full Backend Suite** | `pytest tests/` | **157 / 157** | Complete regression suite (0 failures). |

---

## 6. Key Takeaways for Developers

1. **No Fake Embeddings**: All embeddings come from real forward passes through the model on real image crops.
2. **Modular Architecture**: Layer 2 does not know or care which neural network produced the embedding. You can swap `resnet34_veri776` with another model simply by updating `app/config.py`.
3. **Plates Are Never Required for CityFlow**: Visual re-identification operates smoothly with `plate = None`.
4. **Safety Against Missing Evidence**: Missing modalities do not create artificial 1.0 scores; without plate or appearance, observations cannot be confirmed.
5. **Zero New Pip Dependencies**: Built entirely on existing PyTorch, Torchvision, OpenCV, NumPy, and SQLAlchemy packages.
