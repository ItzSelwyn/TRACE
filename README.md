# TRACE — Tracking, Recognition, Analytics & City-wide Traffic Enforcement

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16 + PostGIS](https://img.shields.io/badge/PostGIS-16--3.4-336791?logo=postgresql&logoColor=white)](https://postgis.net/)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?logo=ultralytics&logoColor=black)](https://ultralytics.com/)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-v2.8-FF6F00?logo=paddlepaddle&logoColor=white)](https://github.com/PaddlePaddle/PaddleOCR)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

> **Problem Statement ID:** 26127  
> **Organization:** Bharat Electronics Limited (BEL)  
> **Category:** Software | **Theme:** Transportation & Logistics  
> **Core Innovation:** A 5-Layer Spatio-Temporal Intelligence Platform linking disparate camera feeds into continuous vehicle trajectories, multimodal identity fusion, and city-scale traffic flow analytics.

---

## 📌 Table of Contents
1. [Overview](#-overview)
2. [Key Capabilities](#-key-capabilities)
3. [The 5-Layer Intelligence Architecture](#-the-5-layer-intelligence-architecture)
4. [Tech Stack](#-tech-stack)
5. [Repository Structure](#-repository-structure)
6. [Prerequisites](#-prerequisites)
7. [Step-by-Step Installation & Run Guide](#-step-by-step-installation--run-guide)
   - [1. Environment Configuration](#1-environment-configuration)
   - [2. Database Setup (PostGIS 16)](#2-database-setup-postgis-16)
   - [3. Backend Setup & Startup](#3-backend-setup--startup)
   - [4. Frontend Setup & Startup](#4-frontend-setup--startup)
   - [5. One-Command Docker Setup](#5-one-command-docker-setup-alternative)
8. [Hardware & dGPU Acceleration](#-hardware--dgpu-acceleration)
9. [Empirical Benchmarks & System Performance](#-empirical-benchmarks--system-performance)
10. [Interactive User Interface Walkthrough](#-interactive-user-interface-walkthrough)
11. [API Reference](#-api-reference)
12. [Evaluation & Verification Scripts](#-evaluation--verification-scripts)
13. [Troubleshooting & FAQs](#-troubleshooting--faqs)
14. [License & Acknowledgments](#-license--acknowledgments)

---

## 🔭 Overview

Modern metropolitan cities operate extensive networks of CCTV and Automatic Number Plate Recognition (ANPR) cameras. However, existing surveillance infrastructure largely operates in **isolated silos**:
* Plates are detected locally without cross-camera temporal or spatial linking.
* Misread, skewed, blurred, or occluded plates result in fragmented or lost trails.
* Law enforcement agencies lack real-time visibility into continuous travel paths across sectors.
* Traffic management control rooms cannot correlate individual vehicle movements with macro-level congestion, origin-destination patterns, or bottleneck emergence.

**TRACE** solves this by unifying distributed camera feeds into an automated, end-to-end vehicle tracking and traffic enforcement system. By combining deep-learning perception with graph-based spatio-temporal reasoning and visual Re-ID feature embeddings, TRACE enables instantaneous vehicle trajectory reconstruction, impossible-journey violation flagging, and dynamic city-wide traffic intelligence.

---

## ⚡ Key Capabilities

* **High-Precision Multi-Camera ANPR (>90% Recognition):**
  Combines YOLOv8 vehicle detection, ByteTrack multi-object tracking, bicubic plate upscaling, and PaddleOCR text extraction with a robust **Temporal OCR Fusion** engine that resolves jitter across consecutive frames.
* **Multimodal Identity Fusion & Vehicle Re-ID:**
  Identifies vehicles across cameras even when license plates are dirty, obscured, or absent by synthesizing **512-dimensional visual appearance embeddings** (ResNet34 VeRi-776 / MobileNetV3), string Levenshtein distance, and spatial-temporal transition probabilities.
* **GIS Trajectory Reconstruction & Impossible Journey Detection:**
  Instantaneously traces any queried vehicle's chronological journey on an interactive MapLibre GIS map. Automatically flags **impossible journeys** where physical speed between camera intervals exceeds feasible road thresholds (detecting cloned or swapped license plates).
* **Macro City-Scale Traffic Analytics:**
  Computes live camera corridor traffic densities, dynamic heatmaps, Origin-Destination (OD) transit matrices, corridor travel times, and congestion forecasts.
* **Real-time Alerting with Operator Verification:**
  Pushes instant alerts over WebSockets for blacklisted vehicles, speed anomalies, and duplicate plates with a dedicated operator review workflow for manual sighting confirmation.

---

## 🏛️ The 5-Layer Intelligence Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TRACE INTELLIGENCE STACK                        │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 5: Prediction & Anomaly Operations                               │
│  - Blacklist Hit Dispatcher • Route Deviation • Operator Verification   │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Network Intelligence & Macro Analytics                        │
│  - GIS Density Heatmaps • Origin-Destination (OD) Matrices • Bottlenecks│
├────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Spatial-Temporal Reasoning Engine                             │
│  - Chronological Trajectory Graph • Impossible Journey Flag (Speed x1.5)│
├────────────────────────────────────────────────────────────────────────┤
│ Layer 2: Multimodal Identity Fusion                                    │
│  - Identity Score = w_plate*S_plate + w_app*S_app + w_time*S_time      │
│  - 512-dim Re-ID Embeddings (VeRi-776) + Levenshtein String Normalizer │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 1: Edge Perception Engine                                        │
│  - YOLOv8 (Vehicle Detection) • ByteTrack (MOT) • PaddleOCR (ANPR)     │
│  - Bicubic Bumper/Plate Localizer • Temporal OCR Fusion Buffer         │
└────────────────────────────────────────────────────────────────────────┘
```

### Data Pipeline Flow
1. **Video Ingestion:** Live RTSP or recorded camera feeds (`c020`, `c023`, `c029`, `c035`, etc.) stream through individual workers coordinated by `CameraScenarioManager`.
2. **Object Detection & Tracking:** YOLOv8 extracts vehicle bounding boxes, class labels (Car, Truck, Bus, Motorcycle), and primary vehicle colors. ByteTrack maintains consistent intra-camera track IDs.
3. **Plate Extraction & Enhancement:** `plate_localizer` pinpoints the bumper/license region, applies bicubic interpolation upscaling, and feeds the crop to PaddleOCR.
4. **Temporal Fusion:** `TemporalOCRFusion` aggregates character-level confidence scores over sliding frame windows, eliminating camera flutter.
5. **Visual Feature Extraction:** Vehicles pass through a PyTorch feature extractor generating normalized 512-dim visual embeddings stored in PostgreSQL via JSONB.
6. **Cross-Camera Association:** `IdentityMatcher` evaluates candidate sightings across road graph edges using spatio-temporal feasibility constraints.
7. **GIS Trajectory & Dispatch:** Validated tracks form canonical vehicle paths on the MapLibre map; blacklist matches immediately trigger alert dispatches.

---

## 💻 Tech Stack

| Layer / Domain | Technologies |
|---|---|
| **Frontend UI/UX** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, MapLibre GL, Recharts |
| **Backend API** | Python 3.11, FastAPI (Async/Await), Pydantic v2, Pydantic Settings, Uvicorn |
| **Database & GIS** | PostgreSQL 16, PostGIS 3.4, SQLAlchemy 2.0 (Asyncpg & Sync), GeoAlchemy2, Alembic |
| **Computer Vision / AI** | Ultralytics YOLOv8, ByteTrack, PaddleOCR (PP-OCRv4), PyTorch, Torchvision, OpenCV, NumPy |
| **Spatial / Graph Algorithms** | NetworkX, Shapely, SciPy, Custom Spatio-Temporal Graph Solver |
| **Security & Auth** | JWT (JSON Web Tokens), Passlib (Bcrypt), Role-Based Access Control (`admin`, `operator`, `analyst`) |
| **DevOps & Containers** | Docker, Docker Compose, Multi-stage builds |

---

## 📁 Repository Structure

```
TRACE/
├── docker-compose.yml              # Multi-container orchestration (PostGIS + FastAPI)
├── .env.example                    # Template environment variables
├── README.md                       # Main project documentation
├── Docs/                           # Formal specifications & PRD/TRD documents
│   ├── TRACE_Agent-Build-Brief_v1.1.md
│   ├── TRACE_App-Website-Flow_v1.1.md
│   ├── TRACE_Backend-Schema_v1.0.md
│   ├── TRACE_MultiModal_ReID_Architecture_Changes.md
│   ├── TRACE_PRD_v1.1.md
│   └── TRACE_TRD_v1.3.md
├── backend/
│   ├── pyproject.toml              # Backend dependencies and packaging
│   ├── Dockerfile                  # Container definition for FastAPI backend
│   ├── alembic.ini                 # Database migration configuration
│   ├── alembic/                    # Database schema migration versions
│   ├── app/
│   │   ├── main.py                 # FastAPI application root & middleware
│   │   ├── config.py               # Pydantic BaseSettings & env loader
│   │   ├── dependencies.py         # JWT security & user role guards
│   │   ├── api/                    # REST & WebSocket route handlers
│   │   │   ├── admin.py            # Camera administration & playback controls
│   │   │   ├── alerts.py           # Real-time alert listings & manual review
│   │   │   ├── analytics.py        # Heatmap, OD-matrix, segment stats, forecasts
│   │   │   ├── auth.py             # User registration, login, and profile
│   │   │   ├── blacklist.py        # Blacklisted plates management & sightings
│   │   │   ├── perception.py       # Live streams, camera status, active telemetry
│   │   │   ├── vehicles.py         # Plate query & GIS trajectory reconstruction
│   │   │   └── ws.py               # Live WebSocket telemetry dispatcher
│   │   ├── db/
│   │   │   ├── models.py           # 15 SQLAlchemy ORM models with PostGIS geometries
│   │   │   ├── session.py          # Async & Sync database session providers
│   │   │   └── seed.py             # Database seeder (cameras, road edges, users)
│   │   ├── modules/
│   │   │   ├── alerts/             # Real-time alert generation & routing
│   │   │   ├── appearance/         # Re-ID visual embedding extraction (VeRi-776)
│   │   │   ├── identity/           # Multi-modal identity fusion & matching
│   │   │   ├── network_intel/      # Macro traffic flow analytics & OD matrices
│   │   │   ├── perception/         # Camera workers, YOLOv8, PaddleOCR, fusion
│   │   │   ├── prediction_anomaly/ # Speed violations & impossible journey logic
│   │   │   └── spatial_temporal/   # Road graph network & trajectory solver
│   │   └── schemas/                # Pydantic request and response models
│   ├── scripts/                    # Offline evaluation & verification utilities
│   │   ├── eval_ocr.py             # Accuracy evaluation on Tamil Nadu (TN) dataset
│   │   ├── live_db_monitor.py      # Real-time DB observation poller
│   │   └── verify_perception.py    # Pipeline regression tests
│   └── tests/                      # Pytest test suite (health, trajectory, auth)
├── frontend/
│   ├── package.json                # Frontend package dependencies & scripts
│   ├── vite.config.ts              # Vite bundler configuration
│   ├── tsconfig.json               # TypeScript compiler config
│   ├── tailwind.config.js          # Tailwind CSS theme & styling tokens
│   └── src/
│       ├── App.tsx                 # Core application shell & navigation
│       ├── components/
│       │   ├── admin/              # Camera feed source & playback manager
│       │   ├── alerts/             # Alerts dashboard with verification dialogs
│       │   ├── analytics/          # Traffic heatmaps, speed graphs, OD matrices
│       │   ├── blacklist/          # Blacklist table & registration modal
│       │   ├── cameras/            # Live camera wall & single camera views
│       │   ├── dashboard/          # City-wide overview, active telemetry cards
│       │   └── vehicle-trace/      # Plate search & MapLibre journey visualizer
│       └── data/                   # Mock scenario configurations & landmarks
└── data/
    ├── footage/                    # Video streams for camera nodes (c020, c023, etc.)
    └── TN/                         # High-resolution benchmark vehicle/plate images
```

---

## 🛠️ Prerequisites

Before getting started, ensure you have the following installed on your host machine:

* **Python:** Version `3.11.x` ([Download Python](https://www.python.org/downloads/))
* **Node.js:** Version `18.x` or `20.x` LTS ([Download Node.js](https://nodejs.org/))
* **Docker & Docker Compose:** ([Download Docker Desktop](https://www.docker.com/products/docker-desktop/))
* **Git:** ([Download Git](https://git-scm.com/))

---

## 🚀 Step-by-Step Installation & Run Guide

### 1. Environment Configuration

Clone the repository and create your local environment file:

```bash
git clone https://github.com/ItzSelwyn/TRACE.git
cd TRACE
```

Copy `.env.example` to `.env`:
```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Ensure your `.env` contains the required parameters:
```ini
# PostgreSQL with PostGIS extension (using 127.0.0.1 to avoid Windows IPv6 collisions)
DATABASE_URL=postgresql+asyncpg://trace:trace@127.0.0.1:5432/trace
DATABASE_URL_SYNC=postgresql://trace:trace@127.0.0.1:5432/trace

# Spatial-Temporal Anomaly Thresholds
IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER=1.5
IDENTITY_CONFIRM_THRESHOLD=0.70
IDENTITY_CANDIDATE_THRESHOLD=0.40
ANALYTICS_WINDOW_SECONDS=300

# Authentication
JWT_SECRET=super_secret_trace_jwt_token_change_in_production
JWT_EXPIRY_MINUTES=480
```

---

### 2. Database Setup (PostGIS 16)

Start the PostGIS database container in detached mode:

```bash
docker compose up -d db
```

*Confirm the database is healthy:*
```bash
docker ps
```
You should see `postgis/postgis:16-3.4` running on port `5432:5432` with status `healthy`.

> **Note for Windows Users:** If you have a native PostgreSQL service installed locally, it may intercept port 5432. Stop it by running `Stop-Service *postgres*` in PowerShell as Administrator.

---

### 3. Backend Setup & Startup

#### Step A: Create and Activate Virtual Environment
```bash
cd backend

# Create Python 3.11 virtual environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate

# Activate on Linux / macOS:
source .venv/bin/activate
```

#### Step B: Install Dependencies & Computer Vision Stack
```bash
pip install --upgrade pip
pip install -e .

# Install computer vision & OCR packages
pip install ultralytics paddlepaddle paddleocr torchvision

# (Recommended for NVIDIA dGPU) Install PyTorch with CUDA 12.1 for real-time 28+ FPS inference:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

> **Model Weights Placement:**
> Ensure neural network weights are placed under `backend/models/`:
> * `yolov8n.pt` — YOLOv8 nano vehicle detection & tracking model
> * `resnet34_veri776_deploy.pt` — ResNet34 512-D vehicle Re-ID metric embedding weights (will auto-fallback to MobileNetV3 if not present)

#### Step C: Run Database Migrations & Seed Baseline Data
```bash
# Apply all Alembic schema migrations (cameras, road edges, scenarios, observations)
alembic upgrade head

# Seed initial corridor cameras, road edges, and default users
python -m app.db.seed
```

#### Step D: Launch FastAPI Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* Backend API will be live at: **`http://localhost:8000`**
* Interactive Swagger Docs: **`http://localhost:8000/docs`**
* ReDoc Documentation: **`http://localhost:8000/redoc`**

---

### 4. Frontend Setup & Startup

Open a new terminal window:

```bash
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```

* The TRACE Web Dashboard will open at: **`http://localhost:3000`** (or `http://localhost:5173`)

---

### 5. One-Command Docker Setup (Alternative)

If you have Docker Desktop running and prefer to run the entire backend and database stack in containers:

```bash
docker compose up --build
```

This will automatically spin up:
1. `trace-db`: PostgreSQL 16 + PostGIS
2. `trace-backend`: FastAPI backend running migrations and seeding on start

Then launch the frontend locally with `cd frontend && npm run dev`.

---

## ⚡ Hardware & dGPU Acceleration

TRACE features native GPU hardware acceleration, allowing high-throughput multi-camera processing on NVIDIA discrete GPUs (such as RTX 3050/4060/A100 series):

* **Dynamic Device Selection (`YOLO_DEVICE`):**
  Configure via `.env`:
  ```ini
  YOLO_DEVICE=auto    # Auto-detect CUDA if available, fallback to CPU
  # Or force explicit device:
  # YOLO_DEVICE=cuda:0
  # YOLO_DEVICE=cpu
  ```
* **Ultralytics YOLOv8 & ByteTrack:** Offloads inference to NVIDIA CUDA cores with automatic FP16 half-precision execution, achieving 28+ FPS per 1080p stream.
* **ResNet34 Appearance Re-ID Extractor:** Evaluates 512-dimensional visual feature vectors on GPU via FP16 PyTorch tensors in under 45 ms per vehicle crop.
* **OpenCV OpenCL Acceleration:** Automated OpenCL acceleration (`cv2.ocl.setUseOpenCL(True)`) for ultra-low latency frame resizing and bumper crop letterboxing.

---

## 📊 Empirical Benchmarks & System Performance

Empirical benchmarks were executed on the end-to-end TRACE pipeline using real CCTV corridor video footage (`c029.mp4`), ground-truth Indian license plate annotations (`data/TN`), and an **NVIDIA GeForce RTX 3050 Laptop GPU** (`cuda:0`).

### 1. Multi-Layer System Performance Summary

| Architectural Layer | Evaluated Component | Empirical Metric | Measured Performance | Operational Standard |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1: Perception** | YOLOv8n Detection & Tracking | **Throughput** | **28.5 FPS** (Steady-State) | $\ge 25$ FPS (Real-time) |
| **Layer 1: Perception** | YOLOv8n Detection & Tracking | **Inference Latency** | **35.05 ms** (Median: 34.11 ms) | $< 50$ ms |
| **Layer 1: Perception** | Multi-Vehicle ByteTrack | **Capacity** | **510 detections** (10.2 / frame) | High-density traffic |
| **Layer 1: ANPR** | Plate Localization & PaddleOCR | **Exact Plate Match** | **90.0%** (9 / 10 exact strings) | $> 85\%$ |
| **Layer 1: ANPR** | Plate Localization & PaddleOCR | **Character Accuracy** | **99.0%** | Alphanumeric precision |
| **Layer 1: ANPR** | Plate Localization & PaddleOCR | **Steady Latency** | **326.6 ms / plate** (Min: 183 ms) | Sub-second edge read |
| **Layer 1: Appearance** | ResNet34 VeRi-776 Embeddings | **Extraction Speed** | **43.87 ms** (22.8 crops/sec) | Real-time Re-ID |
| **Layer 1: Appearance** | 512-D Embedding Normalization | **Hypersphere Norm** | **1.0000** ($\|e\|_2 = 1.0$) | Strict unit metric |
| **Layer 1: Appearance** | Re-ID Discrimination Gap | **Cosine Separation** | **+0.3393** (Intra: 0.988, Inter: 0.649) | Distinct identity gap |
| **Layer 2: Identity Fusion** | Multi-Modal Scoring Engine | **Fusion Throughput** | **17,146 evaluations / sec** | Non-blocking matching |
| **Layer 2: Identity Fusion** | Scoring Evaluation Latency | **Decision Time** | **868.0 $\mu$s** ($0.87$ ms) | Sub-millisecond |
| **Layer 2: Identity Fusion** | Multimodal Match Score | **ANPR Confidence** | **0.944** (Confirmed Match) | Threshold: 0.70 |
| **Layer 3: Spatial Graph** | Trajectory Routing & Reachability| **Graph Capacity** | **11,880 path queries / sec** | Citywide scaling |
| **Layer 3: Spatial Graph** | Shortest-Path Latency | **Dijkstra Traversal** | **84.2 $\mu$s** ($0.084$ ms) | Microsecond routing |
| **Layer 3: Anomaly** | Impossible Journey Detection | **Speed Anomaly** | **Flagged (`too_fast_time`)** | Cloned plate caught |

### 2. Ground-Truth License Plate OCR Accuracy (`data/TN`)

| Image Sample | Ground Truth | OCR Read | Confidence | Exact Match | Character Acc | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TN10.jpg` | `TN69AJ4455` | `TN69AJ4455` | 94.7% | **YES** | 100.0% | 641 ms |
| `TN2.jpg` | `TN76V1978` | `TN76V1978` | 96.9% | **YES** | 100.0% | **183 ms** |
| `TN3.jpg` | `TN02AU9295` | `TN02AU9295` | 92.1% | **YES** | 100.0% | 218 ms |
| `TN4.jpg` | `TN10AR0131` | `TN10AR0131` | 98.2% | **YES** | 100.0% | 457 ms |
| `TN5.jpg` | `TN47T4464` | `TN47T4464` | 95.2% | **YES** | 100.0% | 241 ms |
| `TN6.jpg` | `TN19F0816` | `TN19F0816` | 96.4% | **YES** | 100.0% | 513 ms |
| `TN7.jpg` | `TN07BT5778` | `TN07BT5778` | 90.1% | **YES** | 100.0% | 242 ms |
| `TN8.jpg` | `TN07AP0659` | `TN07AP0659` | 93.3% | **YES** | 100.0% | 245 ms |
| `TN9.jpg` | `TN19Q0835` | `TN19Q0835` | 94.0% | **YES** | 100.0% | 197 ms |
| `TN1.jpg` | `TN63BV7954` | `TN63B7954` | 94.9% | NO | 90.0% | 10,259 ms (cold) |

### 3. Running the Automated Benchmark Suite

To run the automated multi-layer benchmark suite on your local machine:
```bash
cd backend
python scripts/run_benchmarks.py
```
This evaluates all 5 pipeline layers in under 25 seconds and saves full machine-readable telemetry to `backend/benchmark_results.json`.

---

## 🖥️ Interactive User Interface Walkthrough

| View | Purpose & Functionality |
|---|---|
| **Live Operations Dashboard** | Real-time overview of active cameras, total detected vehicles, currently monitored targets, live telemetry cards, and system status indicators. |
| **Camera Network Grid** | Multi-camera CCTV wall streaming synchronized feeds (`c020`, `c023`, `c029`, `c035`). Toggle between raw video and YOLOv8 real-time detection overlays. |
| **Vehicle Trajectory Trace** | Search any license plate (e.g. `TN 37 CY 1234`) to render its complete chronological journey on MapLibre GIS with camera waypoints, timestamps, and impossible-journey anomaly flags. |
| **Traffic Analytics & Heatmaps** | GIS heatmaps indicating traffic density corridors, Origin-Destination (OD) flow matrices, average vehicle speed distributions, and bottleneck congestion forecasts. |
| **Blacklist & Alert Command** | Register blacklisted vehicles with crime classification reasons. Features real-time alert popups and a **Manual Sighting Verification** review workflow. |
| **Camera Administration** | Manage camera node coordinates, scenario offsets, video source switching, and scenario playback synchronizer. |

---

## 📡 API Reference

### Health & System
* `GET /health` — Check backend and database operational status.

### Authentication (`/auth`)
* `POST /auth/register` — Create a new operator, analyst, or admin account.
* `POST /auth/login` — Authenticate and receive a JWT Bearer token.
* `GET /auth/me` — Retrieve authenticated user profile and permissions.

### Vehicle Trajectory & Search
* `GET /vehicles/search?q={plate}` — Search for matching canonical vehicles and last sightings.
* `GET /vehicles/{canonical_vehicle_id}/trajectory` — Fetch full chronological GIS coordinates, timestamps, camera IDs, and speed flags.

### Traffic Analytics (`/analytics`)
* `GET /analytics/heatmap` — Retrieve camera density weights for GIS map heatmap layers.
* `GET /analytics/od-matrix` — Get origin-to-destination transit pair counts.
* `GET /analytics/segments` — Average speeds and volume across road network edges.
* `GET /analytics/forecast` — Short-term congestion risk forecasts.

### Perception & Cameras (`/perception`)
* `GET /perception/cameras` — List all configured cameras with live operational status.
* `GET /perception/camera/{camera_id}/feed` — Stream live annotated MJPEG video.
* `GET /perception/camera/{camera_id}/raw-feed` — Stream live unannotated original MJPEG video.
* `GET /perception/camera/{camera_id}/active-vehicle` — Fetch real-time telemetry of the primary vehicle in frame.
* `GET /perception/status` — Status of background video workers and playback sync.

### Alerts & Blacklist (`/alerts`, `/blacklist`)
* `GET /alerts?status={ALL|VERIFIED|UNVERIFIED}` — Filter live alerts.
* `PATCH /alerts/{id}` — Mark an alert as manually reviewed/verified.
* `GET /blacklist` — Retrieve all active blacklisted plates and last-found camera locations.
* `POST /blacklist` — Add a new plate text and enforcement reason to the database.

### Real-Time WebSocket
* `WS /ws/live` — Bi-directional WebSocket stream for live camera sightings, track updates, and instant alert broadcasts.

---

## 🧪 Evaluation & Verification Scripts

The `backend/scripts/` directory contains automated verification tools for regression testing and evaluation:

### 1. Comprehensive Multi-Layer Benchmark Suite
Benchmark all 5 layers simultaneously (YOLOv8 tracking, OCR accuracy, ResNet34 Re-ID, Layer 2 fusion, and Layer 3 spatial graph routing):
```bash
cd backend
python scripts/run_benchmarks.py
```
*Outputs latency breakdowns, cold vs steady-state FPS, detection counts, OCR accuracy table, cosine separation margins, and saves results to `benchmark_results.json`.*

### 2. License Plate OCR Benchmark
Evaluate OCR accuracy on real-world Indian license plate datasets (e.g. Tamil Nadu `data/TN`):
```bash
cd backend
python scripts/eval_ocr.py
```
*Outputs sample-by-sample ground truth vs predicted plate text, confidence score, exact match rate, and character-level accuracy.*

### 3. Spatio-Temporal Pipeline Verification
Test Layer 1 Perception, Layer 2 Identity Fusion, and Layer 3 Trajectory Reconstruction:
```bash
cd backend
python scripts/verify_layer1_layer2_layer3.py
```

### 4. Real-Time DB & Identity Fusion Monitors
Monitor live observation ingestion and cross-camera identity matching in real time:
```bash
cd backend
python scripts/live_fusion_monitor.py
python scripts/live_db_monitor.py
```

### 5. Automated Pytest Suite
Run unit and integration tests covering API endpoints, impossible journey detection, and database models:
```bash
cd backend
pytest
```

---

## ❓ Troubleshooting & FAQs

#### Q1: PaddleOCR fails with `OneDnnContext does not have the input Filter` or `fused_conv2d`?
* **Cause:** Intel OneDNN (MKL-DNN) CPU acceleration bug on Windows when optimizing convolutions.
* **Fix:** Ensure `enable_mkldnn=False` and `use_gpu=False` are passed when initializing `PaddleOCR` in `ocr_engine.py`, or set the environment flag `FLAGS_use_mkldnn=0`.

#### Q2: Backend reports `password authentication failed for user "trace"` on Windows?
* **Cause:** Windows has a local PostgreSQL service running that takes priority on `localhost:5432` over Docker.
* **Fix:** Use `127.0.0.1` instead of `localhost` in your `.env`, or stop the native Windows service using `Stop-Service *postgres*`.

#### Q3: Database throws `column vehicle_observations.scenario does not exist`?
* **Cause:** The database schema is missing the latest migration columns.
* **Fix:** Apply pending database migrations by running:
  ```bash
  cd backend
  alembic upgrade head
  ```

#### Q4: PaddleOCR throws `IndexError: index 1 is out of bounds for axis 0 with size 1`?
* **Cause:** Micro-crops (< 8px height/width) or non-contiguous image buffers passed to OCR detection.
* **Fix:** Handled automatically in `app/modules/perception/ocr_engine.py` by enforcing a 10px minimum crop threshold, converting images to contiguous 3-channel BGR arrays, and wrapping results in defensive line parsing.

#### Q5: PyTorch warns about `weights_only=False` on model load?
* **Cause:** Recent PyTorch security advisory recommending explicit deserialization flags.
* **Fix:** All checkpoint loads in `AppearanceExtractor` specify `torch.load(resolved, map_location=..., weights_only=True)` to prevent arbitrary code execution during unpickling.

#### Q6: How to force GPU or CPU execution?
* **Cause:** Switching between laptop dGPU and CPU environments.
* **Fix:** Set `YOLO_DEVICE` in your `backend/.env`:
  ```ini
  YOLO_DEVICE=cuda:0   # Forces NVIDIA GPU
  # OR
  YOLO_DEVICE=cpu      # Forces CPU execution
  # OR
  YOLO_DEVICE=auto     # Automatically selects CUDA if available
  ```

#### Q7: Vite frontend warns `maplibre-gl-worker.mjs does not exist in optimize deps`?
* **Cause:** MapLibre GL web worker dynamic bundling in Vite.
* **Fix:** In `frontend/vite.config.ts`, ensure `maplibre-gl` is added to `optimizeDeps.exclude: ['maplibre-gl']`.

---

## 📜 License & Acknowledgments

* Developed for the **Smart India Hackathon (SIH 2026)**.
* Problem Statement **#26127** sponsored by **Bharat Electronics Limited (BEL)**.
* Built with open-source computer vision and geospatial technologies: [YOLOv8](https://github.com/ultralytics/ultralytics), [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [PostGIS](https://postgis.net/), [FastAPI](https://fastapi.tiangolo.com/), and [MapLibre](https://maplibre.org/).