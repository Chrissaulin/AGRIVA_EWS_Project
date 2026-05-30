# TECHNICAL GUIDELINES: AGRIVA Early Warning System (EWS) Web Dashboard

Welcome to the **AGRIVA EWS Web Dashboard** project guidelines. This document outlines the technical architecture, database schemas, directory structure, machine learning inference flows, and step-by-step local setup instructions for running the early warning system application in a local Windows development environment.

---

## 1. Project Directory Structure

We structure the repository cleanly into three primary components:
1. `01_dapur_jupyter`: The existing data science workspace (data files and pickle models).
2. `02_ews_backend`: The FastAPI REST API.
3. `03_ews_frontend`: The React (Vite) single page application.

```text
AGRIVA_EWS_Project/
│
├── 01_dapur_jupyter/                     # Existing Data Science Folder
│   ├── data/
│   │   ├── data_master_clustered.csv     # Historical & Clustered data
│   │   └── data_forecast_ready.csv       # Preprocessed time-series data
│   ├── models_output/
│   │   ├── encoder_provinsi.pkl          # One-Hot Encoder for provinces
│   │   ├── model_forecast_global.pkl     # Multi-Output XGBoost forecaster
│   │   ├── pipeline_ews_biner_cluster_0.pkl
│   │   ├── pipeline_ews_biner_cluster_1.pkl
│   │   └── pipeline_ews_biner_cluster_2.pkl
│   └── notebooks/
│
├── 02_ews_backend/                       # FastAPI REST API Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI Application Entrypoint
│   │   ├── database.py                   # SQLAlchemy Core & Engine Configuration
│   │   ├── models.py                     # SQLAlchemy ORM Models
│   │   ├── schemas.py                    # Pydantic Request & Response Validation
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── predict_service.py        # ML Binary Classification Logic
│   │       └── forecast_service.py       # ML AR-XGBoost Forecasting Logic
│   ├── scripts/
│   │   └── seed_db.py                    # Database Seeding Script (CSV to DB)
│   ├── .env                              # Backend Environment Configurations
│   └── requirements.txt                  # FastAPI, SQLAlchemy, and SciPy dependencies
│
├── 03_ews_frontend/                      # React Frontend (Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── IndonesiaMap.jsx          # Interactive Leaflet Map for EWS
│   │   │   ├── ScenarioForm.jsx          # Custom variable input form for simulation
│   │   │   ├── TrendChart.jsx            # Trend visualizations using Recharts
│   │   │   └── StatCards.jsx             # Visual dashboard metrics
│   │   ├── pages/
│   │   │   ├── Home.jsx                  # Dashboard Landing Page
│   │   │   ├── MapDashboard.jsx          # Geographical Risk Overview
│   │   │   ├── Statistics.jsx            # Trends & Global Forecasting results
│   │   │   └── Simulation.jsx            # Scenario Simulation (Interactive EWS)
│   │   ├── styles/
│   │   │   └── index.css                 # Vanilla CSS Glassmorphic design tokens
│   │   ├── App.jsx                       # Navigation & Routing setup
│   │   └── main.jsx
│   ├── package.json                      # React, Vite, Leaflet, and Recharts dependencies
│   ├── vite.config.js
│   └── index.html
│
├── TECHNICAL_GUIDELINES.md               # This File
└── docker-compose.yml
```

---

## 2. Architecture Overview

### A. Backend Architecture (FastAPI)
The backend is built with **FastAPI** to provide low-latency REST endpoints for data retrieval and ML model inference.
- **Lifespan Context (Cold Start Model Loading)**: ML models (`.pkl` pipelines and forecaster) and lookup data are loaded directly in-memory once at server startup (cold start). This ensures that predictions and database queries respond in milliseconds, completely bypassing runtime disk read overhead.
- **Dynamic Cluster Mapping**: During backend initialization, the application dynamically reads the province-cluster assignments from the master clustered dataset. This dynamic approach removes hardcoded bindings and automatically adapts to any future updates or re-clustering.

### B. Database Design (SQLAlchemy)
The database stores two tables mapping to the primary CSV datasets:

1. **`master_clustered_data`**:
   - `id` (Integer, Primary Key)
   - `date` (Date, Indexed)
   - `region_name` (String, Indexed)
   - `rainfall` (Float)
   - `spi_3m` (Float)
   - `temperature` (Float)
   - `wsi` (Float)
   - `solar_radiation` (Float)
   - `soil_moisture` (Float)
   - `fpar` (Float)
   - `fpar_zscore` (Float)
   - `month` (Integer)
   - `day` (Integer)
   - `dekad_id` (Integer)
   - `target_ews` (Integer)
   - `cluster_wilayah` (Integer, Indexed)
   - `month_extracted` (Integer)

2. **`forecast_ready_data`**:
   - Matches all variables above plus engineered time-series columns (`year`, `dayofyear`, `weekofyear`) and one-hot encoded flags for region mappings (e.g. `region_name_Bali`).

**Flexible Database Adapter**: To facilitate rapid local development and zero-config cold starts, the backend provides an **automatic engine fallback**:
- Checks for a local `DATABASE_URL` environment variable targeting a **PostgreSQL** database.
- If unavailable, it automatically falls back to an offline **SQLite** database (`ews_database.db` inside the backend directory), dynamically creating schemas and running the database seeding script automatically if empty.

### C. Frontend Architecture (React with Vite)
The user interface is structured as a premium single-page application built on **Vite + React**.
- **Aesthetic**: Premium "glassmorphic" styling system utilizing Vanilla CSS variables. Dark-mode color hierarchy, smooth backdrop-blur effects, high contrast readability, and subtle micro-animations for hover states.
- **Geographic Risk Map**: Utilizes **Leaflet** (via React-Leaflet) to render the 33 provinces of Indonesia. Clickable regions, color-coded markers based on Cluster assignments, and quick hover cards displaying critical statistics.
- **Statistical Analytics**: Polished charts built on **Recharts** representing rainfall and temperature trends, agricultural stress markers (FPAR, Soil Moisture), and forecasted indicators.

---

## 3. Core Machine Learning Integration Logic

### A. EWS Interactive Simulation (Page 4)
When a user simulates food security risks for a selected province using specific agricultural variables:
1. **Dynamic Province Mapping**: The backend looks up the selected province's `Cluster_Wilayah` (0, 1, or 2).
2. **Feature Alignment**: User-supplied values are assembled into a structured feature vector matching the model's exact schema:
   `['Rainfall', 'SPI - 3 months', 'Temperature', 'Water Satisfaction Index (WSI)', 'Solar Radiation', 'Soil Moisture (gapfilled historical time series)', 'FPAR', 'FPAR - zscore', 'month_extracted']`
3. **Pipeline Inference**: The features are passed to the correct pipeline `pipeline_ews_biner_cluster_X.pkl`. The pipeline automatically standardizes the features (StandardScaler) and performs inference.
4. **Optimal Threshold Evaluation**: Since precision and recall are optimized for high-sensitivity alerts, predictions are calculated by retrieving `predict_proba()` of the positive class (class 1) and evaluating it against the **cluster-specific optimal threshold**:
   - **Cluster 0**: Threshold = `0.209`
   - **Cluster 1**: Threshold = `0.276`
   - **Cluster 2**: Threshold = `0.244`
   
   If `proba >= threshold`, risk is classified as **Bahaya (1 / Warning)**, else **Aman (0 / Safe)**.

### B. Time-Series Forecasting (Page 3)
When a user requests a regional forecast (e.g. predicting variables 1 to 5 steps/dekads ahead):
1. **Historical Seed Initialization**: The backend queries the database for the selected province's last 3 historical records to construct the initial auto-regressive lag values:
   - `Rainfall_lag_1`, `Rainfall_lag_2`, `Rainfall_lag_3`
   - `Temperature_lag_1`, `Temperature_lag_2`, `Temperature_lag_3`
   - `Soil Moisture_lag_1`, `Soil Moisture_lag_2`, `Soil Moisture_lag_3`
2. **Step-by-Step Rollover Loop**: For each forecasting step forward:
   - Extract the temporal indicators (`year`, `month`, `day`, `dayofyear`, `weekofyear`) based on the simulated date index.
   - Inject the province one-hot encoding array.
   - Run predictions using the global forecaster `model_forecast_global.pkl` for all 8 target variables.
   - Capture predicted values and rollover the lags for the next step:
     - `Lag 3` = `Lag 2`
     - `Lag 2` = `Lag 1`
     - `Lag 1` = `predicted_value`
3. **Response Assembly**: Aggregate step-by-step forecasted records and return the full future trend vector.

---

## 4. Step-by-Step Local Setup

Follow these exact steps inside your PowerShell terminal to launch the dashboard.

### Phase 1: Backend Setup
1. **Navigate to Backend Directory**:
   ```powershell
   cd "c:\Users\faizr\Documents\! Data-Data Faiz\File Kuliah dkk\Semester 4\agriva\AGRIVA_EWS_Project\02_ews_backend"
   ```
2. **Create Python Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
4. **Database Initialization & Seeding**:
   *(If a PostgreSQL instance is running on your system, configure `.env` file first. Otherwise, the script will automatically create `ews_database.db` locally as SQLite fallback.)*
   ```powershell
   python scripts/seed_db.py
   ```
5. **Run the FastAPI Server**:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
   *Verify backend is live by opening [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.*

### Phase 2: Frontend Setup
1. **Open a new terminal window and navigate to Frontend Directory**:
   ```powershell
   cd "c:\Users\faizr\Documents\! Data-Data Faiz\File Kuliah dkk\Semester 4\agriva\AGRIVA_EWS_Project\03_ews_frontend"
   ```
2. **Initialize Vite React Project** (if not created yet):
   ```powershell
   npm install
   ```
3. **Start local Development Server**:
   ```powershell
   npm run dev
   ```
4. **Access UI Dashboard**:
   - Click the output link or navigate to [http://localhost:5173](http://localhost:5173) in your browser.

---

## 5. Summary of REST API Endpoints

The FastAPI server provides the following primary endpoints:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/regions` | `GET` | Get all 33 provinces and their dynamic cluster mappings. |
| `/api/summary` | `GET` | High-level summary metrics (averages of SPI, WSI, temperature) across clusters or provinces. |
| `/api/trends/{region}` | `GET` | Historical rainfall, temperature, and FPAR trend data for charts. |
| `/api/simulate/predict` | `POST` | Input custom variables for a province and output binary EWS prediction (Aman/Bahaya) with probability. |
| `/api/simulate/forecast` | `POST` | Input number of steps for a province and return autoregressive future indicators. |
