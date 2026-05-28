"""
AGRIVA EWS Backend API
FastAPI server for EDA, Map, Prediction, and Forecasting
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib
import os
from typing import List, Optional

app = FastAPI(title="AGRIVA EWS API", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "01_dapur_jupyter", "data")
MODEL_DIR = os.path.join(BASE_DIR, "..", "01_dapur_jupyter", "models_output")

# --- Load Data & Models on Startup ---
df_master = None
df_forecast = None
ews_pipelines = {}
forecast_model = None
province_encoder = None

PROVINCES_LIST = []
CLUSTER_MAP = {}  # province -> cluster_id
FEATURES_EWS = [
    'Rainfall', 'SPI - 3 months', 'Temperature',
    'Water Satisfaction Index (WSI)', 'Solar Radiation',
    'Soil Moisture (gapfilled historical time series)',
    'FPAR', 'FPAR - zscore', 'month_extracted'
]

TARGET_FORECAST_COLS = [
    'Rainfall', 'SPI - 3 months', 'Temperature',
    'Water Satisfaction Index (WSI)', 'Solar Radiation',
    'Soil Moisture (gapfilled historical time series)',
    'FPAR', 'FPAR - zscore'
]


@app.on_event("startup")
def load_resources():
    global df_master, df_forecast, ews_pipelines, forecast_model, province_encoder
    global PROVINCES_LIST, CLUSTER_MAP

    # Load master data
    master_path = os.path.join(DATA_DIR, "data_master_clustered.csv")
    df_master = pd.read_csv(master_path)
    df_master['date'] = pd.to_datetime(df_master['date'])
    df_master['year'] = df_master['date'].dt.year
    if 'target_ews' in df_master.columns:
        df_master['target_biner'] = df_master['target_ews'].apply(lambda x: 0 if x == 0 else 1)

    # Build province -> cluster mapping (most common cluster per province)
    PROVINCES_LIST = sorted(df_master['region_name'].unique().tolist())
    for prov in PROVINCES_LIST:
        cluster = df_master[df_master['region_name'] == prov]['Cluster_Wilayah'].mode().values[0]
        CLUSTER_MAP[prov] = int(cluster)

    # Load EWS pipelines
    for cid in [0, 1, 2]:
        path = os.path.join(MODEL_DIR, f"pipeline_ews_biner_cluster_{cid}.pkl")
        if os.path.exists(path):
            ews_pipelines[cid] = joblib.load(path)

    # Load forecast resources
    forecast_path = os.path.join(MODEL_DIR, "model_forecast_global.pkl")
    if os.path.exists(forecast_path):
        forecast_model = joblib.load(forecast_path)

    encoder_path = os.path.join(MODEL_DIR, "encoder_provinsi.pkl")
    if os.path.exists(encoder_path):
        province_encoder = joblib.load(encoder_path)

    # Load forecast-ready data
    forecast_data_path = os.path.join(DATA_DIR, "data_forecast_ready.csv")
    if os.path.exists(forecast_data_path):
        df_forecast = pd.read_csv(forecast_data_path)
        df_forecast['date'] = pd.to_datetime(df_forecast['date'])

    print("[OK] All resources loaded successfully!")
    print(f"   Provinces: {len(PROVINCES_LIST)}")
    print(f"   EWS Pipelines: {list(ews_pipelines.keys())}")
    print(f"   Forecast Model: {'Loaded' if forecast_model else 'Not Found'}")


# ==================== EDA ENDPOINTS ====================

@app.get("/api/eda/dashboard")
def eda_dashboard(province: Optional[str] = "All", year: Optional[str] = "All"):
    """Comprehensive EDA Dashboard Endpoint"""
    df = df_master.copy()
    
    # Global Filters
    if province != "All" and province in PROVINCES_LIST:
        df = df[df['region_name'] == province]
    if year != "All" and year.isdigit():
        df = df[df['year'] == int(year)]

    if df.empty:
        return {"error": "No data found for selected filters"}

    # 1. KPIs
    avg_rain = float(df['Rainfall'].mean()) if not df.empty else 0
    avg_temp = float(df['Temperature'].mean()) if not df.empty else 0
    
    mode_target = df['target_biner'].mode()
    dominant_status = "Berisiko" if not mode_target.empty and mode_target.iloc[0] == 1 else "Aman"
    
    max_temp = float(df['Temperature'].max()) if not df.empty else 0
    
    # 2. Univariate Distributions
    aman_count = int((df['target_biner'] == 0).sum())
    berisiko_count = int((df['target_biner'] == 1).sum())
    
    # Soil Moisture Histogram (10 bins)
    hist_counts, hist_bins = np.histogram(df['Soil Moisture (gapfilled historical time series)'].dropna(), bins=10)
    soil_moisture_dist = {
        "labels": [f"{round(hist_bins[i], 2)}-{round(hist_bins[i+1], 2)}" for i in range(len(hist_counts))],
        "data": hist_counts.tolist()
    }
    
    # 3. Multivariate
    # Time Series: Rainfall vs WSI per month
    ts_data = df.groupby('month_extracted')[['Rainfall', 'Water Satisfaction Index (WSI)']].mean().reset_index()
    time_series = {
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "rainfall": [float(ts_data[ts_data['month_extracted'] == m]['Rainfall'].mean()) if m in ts_data['month_extracted'].values else 0 for m in range(1, 13)],
        "wsi": [float(ts_data[ts_data['month_extracted'] == m]['Water Satisfaction Index (WSI)'].mean()) if m in ts_data['month_extracted'].values else 0 for m in range(1, 13)]
    }
    
    # Radar Chart: 7 Indicators (Scaled by their max to fit 0-100 radar)
    radar_features = ['Rainfall', 'SPI - 3 months', 'Temperature', 'Water Satisfaction Index (WSI)', 'Solar Radiation', 'Soil Moisture (gapfilled historical time series)', 'FPAR']
    radar_data = []
    for f in radar_features:
        f_max = df_master[f].max()
        f_min = df_master[f].min()
        f_val = df[f].mean()
        # min-max scaling to 0-100
        scaled = ((f_val - f_min) / (f_max - f_min)) * 100 if f_max != f_min else 0
        radar_data.append(round(float(scaled), 2))
        
    # Correlation Heatmap
    corr_cols = radar_features + ['target_biner']
    corr_matrix = df[corr_cols].corr().fillna(0).round(2).to_dict()

    return {
        "kpis": {
            "avg_rainfall": round(avg_rain, 2),
            "avg_temperature": round(avg_temp, 2),
            "dominant_status": dominant_status,
            "max_temp": round(max_temp, 2)
        },
        "target_proportion": {
            "Aman": aman_count,
            "Berisiko": berisiko_count
        },
        "soil_moisture_dist": soil_moisture_dist,
        "time_series": time_series,
        "radar": {
            "labels": ["Rainfall", "SPI-3", "Temp", "WSI", "Solar Rad", "Soil Moist", "FPAR"],
            "data": radar_data
        },
        "correlation": corr_matrix,
        "years": sorted([int(y) for y in df_master['year'].unique()]),
        "provinces": PROVINCES_LIST
    }


# ==================== MAP ENDPOINTS ====================

@app.get("/api/map/data")
def map_data(year: int, month: int):
    """Get province-level warning data for the map"""
    filtered = df_master[(df_master['year'] == year) & (df_master['month_extracted'] == month)]

    if filtered.empty:
        return {"provinces": [], "message": "No data found for the selected period."}

    result = []
    for prov in PROVINCES_LIST:
        prov_data = filtered[filtered['region_name'] == prov]
        if prov_data.empty:
            continue

        # If any record is berisiko (target_biner == 1), mark province as berisiko
        has_risk = int(prov_data['target_biner'].max())
        risk_count = int((prov_data['target_biner'] == 1).sum())
        total_count = len(prov_data)

        # Average feature values
        avg_rainfall = round(float(prov_data['Rainfall'].mean()), 2)
        avg_temp = round(float(prov_data['Temperature'].mean()), 2)
        avg_spi = round(float(prov_data['SPI - 3 months'].mean()), 2)

        result.append({
            "province": prov,
            "warning": "Berisiko" if has_risk else "Aman",
            "warning_code": has_risk,
            "risk_records": risk_count,
            "total_records": total_count,
            "cluster": CLUSTER_MAP.get(prov, -1),
            "avg_rainfall": avg_rainfall,
            "avg_temperature": avg_temp,
            "avg_spi": avg_spi,
        })

    return {"provinces": result, "year": year, "month": month}


@app.get("/api/map/filters")
def map_filters():
    """Get available years and months for map filters"""
    years = sorted(df_master['year'].unique().tolist())
    months = list(range(1, 13))
    return {"years": [int(y) for y in years], "months": months}


# ==================== PREDICTION ENDPOINT ====================

class PredictionRequest(BaseModel):
    province: str
    Rainfall: float
    SPI_3_months: float
    Temperature: float
    WSI: float
    Solar_Radiation: float
    Soil_Moisture: float
    FPAR: float
    FPAR_zscore: float
    month_extracted: int


@app.get("/api/predict/provinces")
def predict_provinces():
    """Get list of provinces and their clusters"""
    return {
        "provinces": [
            {"name": p, "cluster": CLUSTER_MAP.get(p, 0)}
            for p in PROVINCES_LIST
        ]
    }


@app.post("/api/predict/ews")
def predict_ews(req: PredictionRequest):
    """Make EWS prediction"""
    cluster_id = CLUSTER_MAP.get(req.province, 0)

    if cluster_id not in ews_pipelines:
        raise HTTPException(status_code=400, detail=f"Model for cluster {cluster_id} not found.")

    pipeline = ews_pipelines[cluster_id]

    features = np.array([[
        req.Rainfall,
        req.SPI_3_months,
        req.Temperature,
        req.WSI,
        req.Solar_Radiation,
        req.Soil_Moisture,
        req.FPAR,
        req.FPAR_zscore,
        req.month_extracted,
    ]])

    prediction = int(pipeline.predict(features)[0])
    proba = pipeline.predict_proba(features)[0]

    return {
        "province": req.province,
        "cluster": cluster_id,
        "prediction": prediction,
        "status": "Berisiko" if prediction == 1 else "Aman",
        "probability": {
            "aman": round(float(proba[0]), 4),
            "berisiko": round(float(proba[1]), 4),
        }
    }


# ==================== FORECASTING ENDPOINTS ====================

@app.get("/api/forecast/provinces")
def forecast_provinces():
    """Get list of provinces for forecasting"""
    return {"provinces": PROVINCES_LIST}


@app.get("/api/forecast/history")
def forecast_history(province: str, variable: Optional[str] = "Rainfall"):
    """Get historical data for a province and variable"""
    if variable not in TARGET_FORECAST_COLS:
        raise HTTPException(status_code=400, detail=f"Invalid variable: {variable}")

    prov_data = df_master[df_master['region_name'] == province].sort_values('date')

    if prov_data.empty:
        raise HTTPException(status_code=404, detail=f"No data for province: {province}")

    # Return last 108 dekads (~3 years)
    recent = prov_data.tail(108)

    return {
        "province": province,
        "variable": variable,
        "data": [
            {
                "date": row['date'].strftime('%Y-%m-%d'),
                "value": round(float(row[variable]), 3),
                "warning": "Berisiko" if row['target_biner'] == 1 else "Aman",
            }
            for _, row in recent.iterrows()
        ]
    }


@app.post("/api/forecast/predict")
def forecast_predict(province: str, steps: int = 3):
    """Forecast future dekads for a province"""
    if forecast_model is None or province_encoder is None:
        raise HTTPException(status_code=500, detail="Forecast model not loaded.")

    if province not in PROVINCES_LIST:
        raise HTTPException(status_code=400, detail=f"Province '{province}' not found.")

    if steps < 1 or steps > 36:
        raise HTTPException(status_code=400, detail="Steps must be between 1 and 36.")

    # Get the latest data for this province from df_forecast
    prov_data = df_forecast[df_forecast['region_name'] == province].sort_values('date').copy()

    if prov_data.empty:
        raise HTTPException(status_code=404, detail=f"No forecast data for: {province}")

    # Use exact feature names from model
    feature_cols = list(forecast_model.feature_names_in_)
    prov_cols = [c for c in feature_cols if c.startswith('region_name_')]
    lag_src_cols = ['Rainfall', 'Temperature', 'Soil Moisture (gapfilled historical time series)']

    # Get the last row as starting point
    last_row = prov_data.iloc[-1].copy()
    last_date = last_row['date']
    
    # Initialize lag features into last_row for the very first step
    for col in lag_src_cols:
        last_row[f'{col}_lag_1'] = prov_data.iloc[-1][col] if len(prov_data) >= 1 else 0
        last_row[f'{col}_lag_2'] = prov_data.iloc[-2][col] if len(prov_data) >= 2 else 0
        last_row[f'{col}_lag_3'] = prov_data.iloc[-3][col] if len(prov_data) >= 3 else 0

    predictions = []

    for step in range(steps):
        # Calculate next dekad date (~10 days)
        next_date = last_date + pd.Timedelta(days=10)

        # Build feature row
        row_features = {}
        row_features['year'] = next_date.year
        row_features['month'] = next_date.month
        row_features['day'] = next_date.day
        row_features['dayofyear'] = next_date.timetuple().tm_yday
        row_features['weekofyear'] = next_date.isocalendar()[1]

        # Province one-hot encoding
        for col in prov_cols:
            row_features[col] = 1 if f"region_name_{province}" == col else 0

        # Lag features - shift
        for col in lag_src_cols:
            for i in [1, 2, 3]:
                lag_key = f'{col}_lag_{i}'
                row_features[lag_key] = float(last_row[lag_key])

        # Make sure all feature columns are present in exact order
        X_pred = pd.DataFrame([row_features], columns=feature_cols).fillna(0)

        # Predict
        pred = forecast_model.predict(X_pred)[0]
        pred_dict = {TARGET_FORECAST_COLS[i]: round(float(pred[i]), 3) for i in range(len(TARGET_FORECAST_COLS))}

        predictions.append({
            "date": next_date.strftime('%Y-%m-%d'),
            "step": step + 1,
            "predicted": pred_dict,
        })

        # Update last_row for next iteration (auto-regressive)
        for i, col in enumerate(TARGET_FORECAST_COLS):
            last_row[col] = pred[i]
        # Update lag features
        for col in lag_src_cols:
            if f'{col}_lag_3' in last_row:
                last_row[f'{col}_lag_3'] = last_row[f'{col}_lag_2']
            if f'{col}_lag_2' in last_row:
                last_row[f'{col}_lag_2'] = last_row[f'{col}_lag_1']
            if f'{col}_lag_1' in last_row:
                last_row[f'{col}_lag_1'] = pred[TARGET_FORECAST_COLS.index(col)]

        last_date = next_date

    return {
        "province": province,
        "steps": steps,
        "predictions": predictions,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
