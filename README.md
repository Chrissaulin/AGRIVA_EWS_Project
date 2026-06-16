# AGRIVA Early Warning System (EWS)

**AGRIVA EWS** is an end-to-end machine learning platform for drought early warning in Indonesia. It combines historical climate observations, multi-output dekad forecasting, and binary EWS classification per province to support agricultural decision-making at the district level.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Quick Start](#quick-start)
5. [Detailed Setup](#detailed-setup)
6. [Project Structure](#project-structure)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

---

## Project Overview

The system ingests dekad-level (10-day) climate data for all 33 Indonesian provinces, imputes missing values via MICE, scales features with `RobustScaler`, and trains two model families per geospatial cluster:

- **EWS Classifier** — XGBoost binary classifier that predicts drought risk (0 = Aman, 1 = Berisiko).
- **Forecaster** — `MultiOutputRegressor` that predicts 8 climate features 6 months ahead in recursive 10-day steps.

A FastAPI backend exposes the models via REST endpoints consumed by a React frontend. The frontend renders a provincial risk map, time-series charts, prediction forms, and batch forecast dashboards.

---

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │──HTTP│   Backend   │──ORM │ PostgreSQL  │
│  (Nginx +   │      │  (FastAPI   │      │   (v13)     │
│   React)    │      │  Uvicorn)   │      │   :5433     │
└─────────────┘      └──────┬──────┘      └─────────────┘
                            │
                    ┌───────┴───────┐
                    │  ML Models    │
                    │  • classifier │
                    │  • forecaster │
                    │  • scaler     │
                    └──────────────┘
```

| Component | Tech | Port |
|---|---|---|
| Frontend | React + Vite, served by Nginx | `5174` |
| Backend | Python 3.11, FastAPI, Uvicorn | `8001` |
| Database | PostgreSQL 13 | `5433` (host) |
| Notebook (optional) | Jupyter Lab, Python 3.10 | `8888` |

---

## Prerequisites

Before cloning the repository, ensure you have the following installed:

| Tool | Minimum Version | Notes |
|---|---|---|
| **Docker Engine** | 20.10+ | Required for all services |
| **Docker Compose** | 1.29+ / `docker compose` (v2) | Used to orchestrate containers |
| **Git** | 2.30+ | To clone the repository |
| **(Optional) Python** | 3.11+ | Only needed for local backend development outside Docker |
| **(Optional) Node.js** | 18+ | Only needed for local frontend development outside Docker |

> **Windows users**: Use PowerShell (not Git Bash) for Docker commands to avoid TTY issues.

---

## Quick Start

One-command deployment after cloning:

```bash
docker compose up --build -d
```

Then verify:

```bash
docker compose ps
curl http://localhost:8001/api/health
```

Browse to:

| Service | URL |
|---|---|
| Frontend | `http://localhost:5174` |
| Backend API docs | `http://localhost:8001/docs` |
| Jupyter Lab | `http://localhost:8888` (token: `agriva`) |

---

## Detailed Setup

### 1. Clone the Repository

```bash
git clone https://github.com/<org>/AGRIVA_EWS_Project.git
cd AGRIVA_EWS_Project
```

### 2. Configure Environment Variables

No `.env` file is required for basic setup — credentials are already set in `docker-compose.yml`:

```yaml
DATABASE_URL: postgresql://agriva_user:agriva_pass@db:5432/agriva_db
```

If you need to override:

```bash
# Linux/macOS
export DATABASE_URL=postgresql://custom_user:custom_pass@db:5432/custom_db

# Windows PowerShell
$env:DATABASE_URL="postgresql://custom_user:custom_pass@db:5432/custom_db"
```

### 3. Start All Services

```bash
docker compose up --build
```

**Background mode** (recommended):

```bash
docker compose up --build -d
```

**First-run behavior**: The backend `on_event("startup")` hook checks if the database is empty. If `province` or `historical_metric` tables are empty, it automatically runs the ETL seeder (`scripts/etl_seeder.py`) to populate them from `01_dapur_jupyter/data/data_master_clustered_final.csv`.

### 4. Recreate Containers After Config Changes

If you change the `docker-compose.yml` (e.g., add volumes or health checks):

```bash
docker compose down
docker compose up --build -d
```

If you change Python dependencies in `backend/requirements.txt` or Jupyter dependencies in `01_dapur_jupyter/requirements.txt`:

```bash
docker compose build --no-cache
docker compose up -d
```

---

## Project Structure

```
AGRIVA_EWS_Project/
├── docker-compose.yml          # Service orchestration (db, backend, frontend)
├── postgres/
│   └── conf/
│       └── pg_hba.conf         # PostgreSQL HBA rules for Docker networking
├── backend/
│   ├── Dockerfile              # Python 3.11 + libgomp1 (LightGBM runtime)
│   ├── .dockerignore
│   ├── requirements.txt        # Python dependencies
│   ├── main.py                 # FastAPI app, startup hooks, model loading
│   ├── database.py             # SQLAlchemy engine + session factory
│   ├── models.py               # ORM: Province, HistoricalMetric, Forecast*
│   ├── shared.py               # Module-level caches for loaded models
│   ├── core/
│   │   └── config.py           # Constants: feature lists, directories
│   ├── routers/                # API route handlers
│   │   ├── eda.py              # Exploratory data analysis endpoints
│   │   ├── map.py              # Provincial risk map data
│   │   ├── forecast.py         # 6-month forecast generation + retrieval
│   │   ├── predict.py          # Single-province manual EWS prediction
│   │   ├── simulate.py         # Batch CSV upload simulation
│   │   └── admin.py            # Admin utilities (re-seed, trigger forecast)
│   ├── services/               # Business logic
│   │   ├── scaling_service.py  # RobustScaler scale_input / unscale_output
│   │   ├── predict_service.py  # predict_ews_endpoint + forecast_predict
│   │   ├── forecast_service.py # Batch forecast orchestration
│   │   ├── ews_service.py      # XGBoost pipeline wrapper
│   │   ├── feature_engineering.py # Lag/rolling feature generation
│   │   └── etl_service.py      # CSV parsing + DB seeding
│   ├── ml/                     # Model loading utilities
│   │   ├── loader.py           # Loads .pkl bundles from models_output
│   │   ├── predictor.py        # EWSPredictor class
│   │   └── feature_builder.py  # Feature matrix construction
│   ├── repositories/           # Data access layer
│   ├── schemas/                # Pydantic request/response models
│   ├── scripts/
│   │   └── etl_seeder.py       # Initial DB population on empty startup
│   └── tests/                  # Pytest suite
├── 01_dapur_jupyter/
│   ├── Dockerfile              # Jupyter Lab (Python 3.10, token: agriva)
│   ├── data/
│   │   ├── asap_indonesia_master_2001.csv   # Raw unscaled climate data
│   │   └── data_master_clustered_final.csv  # Processed + clustered data
│   ├── models/
│   │   ├── agriva_master_classifier.pkl     # Trained EWS pipeline (XGBoost)
│   │   ├── agriva_master_forecasting.pkl    # Trained forecaster bundle
│   │   └── scaler_stats.json                # RobustScaler center/scale params
│   └── notebooks/
│       ├── 01_EDA_Preprocessing_AGRIVA(nv).ipynb
│       ├── 02_Modeling_AGRIVA_EWS(nv).ipynb
│       └── 03_Modeling_AGRIVA_Forecasting(nv).ipynb
└── frontend/
    ├── nginx.conf              # Reverse proxy config
    └── (React app sources)
```

### Bind Mounts (Docker → Host)

| Host Path | Container Path | Purpose |
|---|---|---|
| `./01_dapur_jupyter/data` | `/app/raw_data:ro` | Raw + processed CSVs for ETL |
| `./01_dapur_jupyter/models` | `/app/models_output:ro` | `.pkl` models + `scaler_stats.json` |
| `./backend` | `/app` | Live-reload source code during dev |
| `./frontend` | `/usr/share/nginx/html:ro` | Served static assets |

---

## API Reference

### Health Check

```bash
GET http://localhost:8001/api/health
```

### Provincial Risk Map

```bash
GET http://localhost:8001/api/map/data?year=2026&month=1&mode=historical
```

Response fields per province:

| Field | Type | Description |
|---|---|---|
| `province` | str | Province name (33 Indonesian provinces) |
| `warning` | str | `"Berisiko"` or `"Aman"` |
| `warning_code` | int | `1` = Berisiko, `0` = Aman |
| `avg_rainfall` | float | mm/month (unscaled) |
| `avg_temperature` | float | °C (unscaled) |
| `avg_spi` | float | 3-month SPI (unscaled) |
| `cluster` | int | Climate cluster (0, 1, or 2) |

### Manual EWS Prediction

```bash
POST http://localhost:8001/api/predict/ews
Content-Type: application/json

{
  "province": "Jawa Barat",
  "Rainfall": 120.5,
  "SPI_3_months": 0.8,
  "Temperature": 26.3,
  "WSI": 95.0,
  "Solar_Radiation": 170000.0,
  "Soil_Moisture": 0.35,
  "FPAR": 65.2,
  "FPAR_zscore": 0.05
}
```

### Trigger Forecast Batch

```bash
POST http://localhost:8001/api/forecast/trigger
Content-Type: application/json

{ "months_ahead": 6 }
```

### Retrieve Forecast Results

```bash
GET http://localhost:8001/api/forecast/data?batch_id=<latest_batch_id>
```

---

## Data Seeding

If the database is empty or corrupt, force a re-seed from the processed CSV:

```bash
# Via API (requires running backend)
curl -X POST http://localhost:8001/api/admin/seed

# Or restart the backend — it auto-seeds on empty tables
docker compose restart backend
```

---

## Troubleshooting

### `FATAL: no pg_hba.conf entry for host ...`

**Cause**: A stale PostgreSQL data volume was initialized on a different Docker network subnet.

**Fix**: Recreate the volume:

```bash
docker compose down
docker volume rm <project>_pg_data
docker compose up -d
```

The custom `postgres/conf/pg_hba.conf` mounted in `docker-compose.yml` prevents this on fresh clones, but existing volumes may still fail.

### `FileNotFoundError: scaler_stats.json`

**Cause**: The `scaler_stats.json` file is missing from `01_dapur_jupyter/models/`.

**Fix**: Ensure the file exists in the repository (it is tracked in git at `01_dapur_jupyter/models/scaler_stats.json`). If missing, regenerate it from the raw data:

```bash
python scripts/generate_scaler_stats.py
```

### Backend crashes with `sklearn` version warning

**Cause**: The model was pickled with `scikit-learn 1.4.2` but the Docker image runs `1.9.x`.

**Impact**: The warning is non-fatal but may produce deserialization edge cases. Pin the backend image to a matching Python version if strict reproducibility is needed.

### Port already in use

```bash
# Change ports in docker-compose.yml under each service's `ports:`
# e.g., frontend: "3000:80" instead of "5174:80"
```

### Jupyter token doesn't work

Default token is `agriva`. To reset:

```bash
docker compose exec jupyter jupyter server list
docker compose exec jupyter jupyter notebook stop 8888
docker compose exec jupyter jupyter lab --NotebookApp.token=''
```

---

## License

Internal project — AGRIVA Team.
