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
8. [Interactive User Interface Walkthrough](#-interactive-user-interface-walkthrough)
9. [API Reference](#-api-reference)
10. [Evaluation & Verification Scripts](#-evaluation--verification-scripts)
11. [Troubleshooting & FAQs](#-troubleshooting--faqs)
12. [License & Acknowledgments](#-license--acknowledgments)

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

#### Step B: Install Dependencies
```bash
pip install --upgrade pip
pip install -e .

# Install computer vision & OCR packages
pip install ultralytics paddlepaddle paddleocr torchvision
```

#### Step C: Run Migrations & Seed Baseline Data
```bash
# Apply Alembic schema migrations
alembic upgrade head

# Seed initial cameras, road edges, and default users
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

### 1. License Plate OCR Benchmark
Evaluate OCR accuracy on real-world Indian license plate datasets (e.g. Tamil Nadu `data/TN`):
```bash
cd backend
python scripts/eval_ocr.py
```
*Outputs sample-by-sample ground truth vs predicted plate text, confidence score, exact match rate, and character-level accuracy.*

### 2. Spatio-Temporal Pipeline Verification
Test Layer 1 Perception, Layer 2 Identity Fusion, and Layer 3 Trajectory Reconstruction:
```bash
cd backend
python scripts/verify_layer1_layer2_layer3.py
```

### 3. Automated Pytest Suite
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

#### Q3: Vite frontend warns `maplibre-gl-worker.mjs does not exist in optimize deps`?
* **Cause:** MapLibre GL web worker dynamic bundling in Vite.
* **Fix:** In `frontend/vite.config.ts`, ensure `maplibre-gl` is added to `optimizeDeps.exclude: ['maplibre-gl']`.

---

## 📜 License & Acknowledgments

* Developed for the **Smart India Hackathon (SIH 2026)**.
* Problem Statement **#26127** sponsored by **Bharat Electronics Limited (BEL)**.
* Built with open-source computer vision and geospatial technologies: [YOLOv8](https://github.com/ultralytics/ultralytics), [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [PostGIS](https://postgis.net/), [FastAPI](https://fastapi.tiangolo.com/), and [MapLibre](https://maplibre.org/).