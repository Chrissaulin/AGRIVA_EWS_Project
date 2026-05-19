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

@app.get("/api/eda/summary")
def eda_summary():
    """Dataset summary statistics for the Home page"""
    rows, cols = df_master.shape
    provinces = PROVINCES_LIST
    years = sorted(df_master['year'].unique().tolist())
    year_range = f"{min(years)} - {max(years)}"

    # Target distribution (biner)
    aman_count = int((df_master['target_biner'] == 0).sum())
    berisiko_count = int((df_master['target_biner'] == 1).sum())

    # Cluster distribution
    cluster_dist = df_master['Cluster_Wilayah'].value_counts().sort_index().to_dict()
    cluster_dist = {f"Cluster {k}": int(v) for k, v in cluster_dist.items()}

    # Feature statistics
    feature_stats = {}
    for feat in FEATURES_EWS[:-1]:  # exclude month_extracted
        if feat in df_master.columns:
            feature_stats[feat] = {
                "min": round(float(df_master[feat].min()), 3),
                "max": round(float(df_master[feat].max()), 3),
                "mean": round(float(df_master[feat].mean()), 3),
                "std": round(float(df_master[feat].std()), 3),
            }

    # Monthly distribution of berisiko
    monthly_risk = df_master[df_master['target_biner'] == 1].groupby('month_extracted').size()
    monthly_risk_dict = {int(k): int(v) for k, v in monthly_risk.items()}

    # Province risk count
    prov_risk = df_master[df_master['target_biner'] == 1].groupby('region_name').size().sort_values(ascending=False)
    prov_risk_dict = {k: int(v) for k, v in prov_risk.items()}

    return {
        "dataset": {
            "rows": rows,
            "columns": cols,
            "year_range": year_range,
            "total_provinces": len(provinces),
            "provinces": provinces,
        },
        "target_distribution": {
            "Aman": aman_count,
            "Berisiko": berisiko_count,
            "total": aman_count + berisiko_count,
        },
        "cluster_distribution": cluster_dist,
        "feature_stats": feature_stats,
        "monthly_risk": monthly_risk_dict,
        "province_risk": prov_risk_dict,
        "model_info": {
            "algorithm": "XGBoost Classifier",
            "pipeline": "SMOTE → StandardScaler → XGBoost",
            "clusters": 3,
            "features_used": FEATURES_EWS,
            "target": "Binary (Aman / Berisiko)",
        }
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

    # We need lag features from the last rows
    lag_cols = [col for col in prov_data.columns if '_lag_' in col]
    time_features = ['year', 'month', 'day', 'dayofyear', 'weekofyear']
    prov_cols = [col for col in prov_data.columns if col.startswith('region_name_')]
    feature_cols = time_features + prov_cols + lag_cols

    # Get the last row as starting point
    last_row = prov_data.iloc[-1].copy()
    last_date = last_row['date']

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
            row_features[col] = last_row[col] if col in last_row else 0

        # Lag features - shift
        lag_src_cols = ['Rainfall', 'Temperature', 'Soil Moisture (gapfilled historical time series)']
        for col in lag_src_cols:
            for i in [1, 2, 3]:
                lag_key = f'{col}_lag_{i}'
                if i == 1:
                    row_features[lag_key] = float(last_row[col]) if col in last_row else 0
                elif i == 2:
                    prev_lag = f'{col}_lag_1'
                    row_features[lag_key] = float(last_row[prev_lag]) if prev_lag in last_row else 0
                elif i == 3:
                    prev_lag = f'{col}_lag_2'
                    row_features[lag_key] = float(last_row[prev_lag]) if prev_lag in last_row else 0

        # Make sure all feature columns are present
        X_pred = pd.DataFrame([row_features])
        for col in feature_cols:
            if col not in X_pred.columns:
                X_pred[col] = 0
        X_pred = X_pred[feature_cols]

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
