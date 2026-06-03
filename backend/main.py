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
MODEL_DIR = os.path.join(BASE_DIR, "..", "01_dapur_jupyter", "models")

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
    master_path = os.path.join(DATA_DIR, "data_master_clustered_final.csv")
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

    # Load EWS pipelines (now a single dictionary keyed by cluster_id)
    ews_path = os.path.join(MODEL_DIR, "agriva_master_classifier.pkl")
    if os.path.exists(ews_path):
        ews_pipelines = joblib.load(ews_path)

    # Load forecast resources (now a single dictionary keyed by cluster_id -> target -> model)
    forecast_path = os.path.join(MODEL_DIR, "agriva_master_forecaster.pkl")
    if os.path.exists(forecast_path):
        forecast_model = joblib.load(forecast_path)

    # We will use df_master for both EDA and forecasting now since it contains all historical data and lags
    df_forecast = df_master.copy()

    print("[OK] All resources loaded successfully!")
    print(f"   Provinces: {len(PROVINCES_LIST)}")
    print(f"   EWS Pipelines: {'Loaded' if ews_pipelines else 'Not Found'}")
    print(f"   Forecast Model: {'Loaded' if forecast_model else 'Not Found'}")


# ==================== EDA ENDPOINTS ====================

@app.get("/api/eda/dashboard")
def eda_dashboard(province: Optional[str] = "All", year: Optional[str] = "All", dist_feature: Optional[str] = "Soil Moisture (gapfilled historical time series)"):
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
    
    # Dynamic Feature Histogram (10 bins)
    if dist_feature and dist_feature in df.columns:
        hist_counts, hist_bins = np.histogram(df[dist_feature].dropna(), bins=10)
        feature_dist = {
            "labels": [f"{round(hist_bins[i], 2)}-{round(hist_bins[i+1], 2)}" for i in range(len(hist_counts))],
            "data": hist_counts.tolist()
        }
    else:
        feature_dist = {"labels": [], "data": []}
    
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
        
    # Scatter Plot Data (Sampled)
    scatter_df = df.sample(n=min(300, len(df)), random_state=42)[['Rainfall', 'Soil Moisture (gapfilled historical time series)', 'target_biner']].dropna()
    scatter_data = {
        "aman": [{"x": float(row['Rainfall']), "y": float(row['Soil Moisture (gapfilled historical time series)'])} for _, row in scatter_df[scatter_df['target_biner'] == 0].iterrows()],
        "berisiko": [{"x": float(row['Rainfall']), "y": float(row['Soil Moisture (gapfilled historical time series)'])} for _, row in scatter_df[scatter_df['target_biner'] == 1].iterrows()]
    }

    # Data Table Summary
    if province == "All":
        table_df = df.groupby('region_name')[radar_features + ['target_biner']].mean().reset_index()
        table_df['target_biner'] = df.groupby('region_name')['target_biner'].sum().reset_index()['target_biner']
        table_df = table_df.head(15).round(2)
        table_data = table_df.rename(columns={'region_name': 'Kategori'}).to_dict(orient='records')
    else:
        table_df = df.groupby('year')[radar_features + ['target_biner']].mean().reset_index()
        table_df['target_biner'] = df.groupby('year')['target_biner'].sum().reset_index()['target_biner']
        table_df = table_df.head(15).round(2)
        table_data = table_df.rename(columns={'year': 'Kategori'}).to_dict(orient='records')

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
        "feature_dist": feature_dist,
        "time_series": time_series,
        "radar": {
            "labels": ["Curah Hujan", "Indeks Kekeringan (SPI)", "Suhu Udara", "Kecukupan Air (WSI)", "Radiasi Matahari", "Kelembaban Tanah", "Pertumbuhan Vegetasi (FPAR)"],
            "data": radar_data
        },
        "scatter": scatter_data,
        "table_data": table_data,
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

    model_dict = ews_pipelines[cluster_id]
    pipeline = model_dict['model_xgboost']
    threshold = model_dict['threshold_siaga']

    # Get latest historical row for this province to fill in lag and rolling features
    prov_data = df_master[df_master['region_name'] == req.province].sort_values('date')
    if prov_data.empty:
        raise HTTPException(status_code=404, detail="Province data not found")
    
    last_row = prov_data.iloc[-1].copy()
    
    # Overwrite the core features with the user's simulation inputs
    last_row['Rainfall'] = req.Rainfall
    last_row['SPI - 3 months'] = req.SPI_3_months
    last_row['Temperature'] = req.Temperature
    last_row['Water Satisfaction Index (WSI)'] = req.WSI
    last_row['Solar Radiation'] = req.Solar_Radiation
    last_row['Soil Moisture (gapfilled historical time series)'] = req.Soil_Moisture
    last_row['FPAR'] = req.FPAR
    last_row['FPAR - zscore'] = req.FPAR_zscore
    last_row['month_extracted'] = req.month_extracted

    # Ensure all required features are present in the exact order
    feature_cols = list(pipeline.feature_names_in_)
    features = pd.DataFrame([last_row])[feature_cols].fillna(0)

    # Predict probability
    proba = pipeline.predict_proba(features)[0]
    prob_berisiko = float(proba[1])
    
    # Apply custom threshold
    prediction = 1 if prob_berisiko >= threshold else 0

    return {
        "province": req.province,
        "cluster": cluster_id,
        "prediction": prediction,
        "status": "Berisiko" if prediction == 1 else "Aman",
        "probability": {
            "aman": round(float(proba[0]), 4),
            "berisiko": round(prob_berisiko, 4),
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
    if forecast_model is None:
        raise HTTPException(status_code=500, detail="Forecast model not loaded.")

    if province not in PROVINCES_LIST:
        raise HTTPException(status_code=400, detail=f"Province '{province}' not found.")

    if steps < 1 or steps > 36:
        raise HTTPException(status_code=400, detail="Steps must be between 1 and 36.")

    # Get the latest data for this province from df_master
    prov_data = df_master[df_master['region_name'] == province].sort_values('date').tail(100).copy()

    if prov_data.empty:
        raise HTTPException(status_code=404, detail=f"No forecast data for: {province}")

    cluster_id = CLUSTER_MAP.get(province, 0)
    if forecast_model is None or cluster_id not in forecast_model:
        raise HTTPException(status_code=500, detail=f"Forecast model for cluster {cluster_id} not found.")

    forecaster_dict = forecast_model[cluster_id]
    
    # Use exact feature names from the first model
    feature_cols = list(forecaster_dict[TARGET_FORECAST_COLS[0]].feature_names_in_)

    predictions = []

    for step in range(steps):
        last_date = pd.to_datetime(prov_data['date'].iloc[-1])
        next_date = last_date + pd.Timedelta(days=10)

        # Create new feature dict from the LAST row (to forward fill static/long-term features)
        new_row = prov_data.iloc[-1].to_dict()

        # Update time features
        new_row['date'] = next_date
        new_row['month'] = next_date.month
        new_row['day'] = next_date.day
        new_row['dekad_id'] = next_date.day // 10 + 1
        new_row['year_extracted'] = next_date.year
        new_row['month_extracted'] = next_date.month
        new_row['quarter_extracted'] = (next_date.month - 1) // 3 + 1
        new_row['semester_extracted'] = 1 if next_date.month <= 6 else 2

        # Update short-term lags and rolling features dynamically
        for target in TARGET_FORECAST_COLS:
            if len(prov_data) >= 1:
                val_1 = prov_data[target].iloc[-1]
                new_row[f'{target}_lag1'] = val_1
                new_row[f'{target}_lag_1'] = val_1
            
            if len(prov_data) >= 3:
                val_3 = prov_data[target].iloc[-3]
                new_row[f'{target}_lag3'] = val_3
                new_row[f'{target}_lag_3'] = val_3
                
            if len(prov_data) >= 6:
                val_6 = prov_data[target].iloc[-6]
                new_row[f'{target}_lag_6'] = val_6
                
            if len(prov_data) >= 3:
                val_rm3 = prov_data[target].iloc[-3:].mean()
                new_row[f'{target}_rollmean3'] = val_rm3

        # Prepare X_pred with exact columns
        X_pred = pd.DataFrame([new_row])[feature_cols].fillna(0)

        # Predict each target separately
        pred_dict = {}
        for target in TARGET_FORECAST_COLS:
            if target in forecaster_dict:
                pred_val = forecaster_dict[target].predict(X_pred)[0]
                pred_dict[target] = round(float(pred_val), 3)
                new_row[target] = pred_val
            else:
                pred_dict[target] = 0
                new_row[target] = 0

        predictions.append({
            "date": next_date.strftime('%Y-%m-%d'),
            "step": step + 1,
            "predicted": pred_dict,
        })

        # Append predicted row to history for autoregressive lags
        prov_data = pd.concat([prov_data, pd.DataFrame([new_row])], ignore_index=True)

    return {
        "province": province,
        "steps": steps,
        "predictions": predictions,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
