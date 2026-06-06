"""
Prediction service.
Shared predict_ews and forecast_predict logic used by routers.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

import core.config as config
import models
from services.ews_service import predict_ews
from shared import get_province_dataframe_with_features
from sqlalchemy.orm import Session


def predict_ews_endpoint(request, db: Session) -> dict[str, Any]:
    """
    Handle /api/predict/ews request body.
    Accepts either a PredictionRequest instance or a plain dict.
    """
    from schemas.predict import PredictionRequest

    if not isinstance(request, PredictionRequest):
        request = PredictionRequest(**request)

    cluster_id = config.CLUSTER_MAP.get(request.province, 0)

    df_prov = get_province_dataframe_with_features(request.province, db)
    if df_prov.empty:
        raise ValueError("Province data not found in database.")

    last_row = df_prov.sort_values("date").iloc[-1].copy()
    last_row["Rainfall"] = request.Rainfall
    last_row["SPI - 3 months"] = request.SPI_3_months
    last_row["Temperature"] = request.Temperature
    last_row["Water Satisfaction Index (WSI)"] = request.WSI
    last_row["Solar Radiation"] = request.Solar_Radiation
    last_row["Soil Moisture (gapfilled historical time series)"] = request.Soil_Moisture
    last_row["FPAR"] = request.FPAR
    last_row["FPAR - zscore"] = request.FPAR_zscore
    last_row["month_extracted"] = request.month_extracted

    from shared import ews_pipeline

    if ews_pipeline is None:
        raise RuntimeError("EWS Master Pipeline not loaded.")

    if isinstance(ews_pipeline, dict):
        if cluster_id not in ews_pipeline:
            raise ValueError(f"Model for cluster {cluster_id} not found.")
        cluster_dict = ews_pipeline[cluster_id]
        if isinstance(cluster_dict, dict) and "model_xgboost" in cluster_dict:
            pipeline = cluster_dict["model_xgboost"]
            threshold = cluster_dict.get("threshold_siaga", 0.5)
        else:
            pipeline = cluster_dict
            threshold = 0.5
    else:
        pipeline = ews_pipeline
        threshold = 0.5

    feature_cols = list(pipeline.feature_names_in_)
    features = pd.DataFrame([last_row])[feature_cols].fillna(0)
    ews_result = predict_ews(cluster_id, features, threshold=threshold, pipeline_override=pipeline)

    try:
        prov_obj = db.query(models.Province).filter(models.Province.name == request.province).first()
        session_record = models.SimulationSession(
            source_filename="manual_form",
            province_id=prov_obj.id if prov_obj else None,
            cluster_used=cluster_id,
            ews_label=ews_result["ews_label"],
            ews_probability=ews_result["ews_probability"],
            row_count=1,
            notes="Single EWS manual prediction simulated via API.",
        )
        db.add(session_record)
        db.commit()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to write simulation session: %s", exc)

    return {
        "province": request.province,
        "cluster": cluster_id,
        "prediction": ews_result["ews_label"],
        "status": "Berisiko" if ews_result["ews_label"] == 1 else "Aman",
        "probability": {
            "aman": round(float(1.0 - ews_result["ews_probability"]), 4),
            "berisiko": round(float(ews_result["ews_probability"]), 4),
        },
        "threshold": round(float(ews_result["threshold"]), 4),
    }


def forecast_predict(province: str, steps: int, db: Session) -> dict[str, Any]:
    """
    Handle /api/forecast/predict logic.
    """
    from shared import forecast_model
    import numpy as np

    if forecast_model is None:
        raise RuntimeError("Forecast model not loaded.")

    if province not in config.PROVINCES_LIST:
        raise ValueError(f"Province '{province}' not found.")

    if not (0 <= steps <= 36):
        raise ValueError("Steps must be between 0 and 36.")

    df_prov = get_province_dataframe_with_features(province, db)
    if df_prov.empty:
        raise ValueError(f"No historical metrics found for province: {province}")

    prov_data = df_prov.sort_values("date").tail(100).copy()
    cluster_id = config.CLUSTER_MAP.get(province, 0)

    if cluster_id not in forecast_model:
        raise ValueError(f"Forecast model for cluster {cluster_id} not found.")

    cluster_models = forecast_model[cluster_id]
    predictions: list[dict] = []

    for step in range(steps):
        last_date = pd.to_datetime(prov_data["date"].iloc[-1])
        next_date = last_date + pd.Timedelta(days=10)
        new_row = prov_data.iloc[-1].to_dict()

        new_row["date"] = next_date
        new_row["month"] = next_date.month
        new_row["day"] = next_date.day
        new_row["dekad_id"] = next_date.day // 10 + 1
        new_row["year_extracted"] = next_date.year
        new_row["month_extracted"] = next_date.month
        new_row["quarter_extracted"] = (next_date.month - 1) // 3 + 1
        new_row["semester_extracted"] = 1 if next_date.month <= 6 else 2
        new_row["dayofyear"] = next_date.dayofyear
        new_row["weekofyear"] = next_date.isocalendar()[1]

        for t in config.TARGET_FORECAST_COLS:
            if len(prov_data) >= 1:
                val1 = prov_data[t].iloc[-1]
                new_row[f"{t}_lag_1"] = val1
                new_row[f"{t}_lag1"] = val1
            if len(prov_data) >= 2:
                new_row[f"{t}_lag_2"] = prov_data[t].iloc[-2]
            if len(prov_data) >= 3:
                val3 = prov_data[t].iloc[-3]
                new_row[f"{t}_lag_3"] = val3
                new_row[f"{t}_lag3"] = val3
                rm3 = prov_data[t].iloc[-3:].mean()
                new_row[f"{t}_rollmean3"] = rm3
            if len(prov_data) >= 6:
                new_row[f"{t}_lag_6"] = prov_data[t].iloc[-6]

        pred_dict: dict[str, float] = {}
        for target in config.TARGET_FORECAST_COLS:
            if target in cluster_models:
                m = cluster_models[target]
                f_cols = list(m.feature_names_in_)
                X_pred = pd.DataFrame([new_row]).reindex(columns=f_cols, fill_value=0)
                pred_val = round(float(m.predict(X_pred)[0]), 3)
                pred_dict[target] = pred_val
                new_row[target] = pred_val

        predictions.append(
            {
                "date": next_date.strftime("%Y-%m-%d"),
                "step": step + 1,
                "predicted": pred_dict,
            }
        )
        prov_data = pd.concat([prov_data, pd.DataFrame([new_row])], ignore_index=True)

    historical_dates: list[str] = []
    historical_actual: dict[str, list[float]] = {}
    historical_pred: dict[str, list[float]] = {}
    hist_df = df_prov.sort_values("date").tail(36).copy()
    if not hist_df.empty:
        historical_dates = [
            pd.to_datetime(d).strftime("%Y-%m-%d") for d in hist_df["date"]
        ]
        for target in config.TARGET_FORECAST_COLS:
            if target in cluster_models:
                m = cluster_models[target]
                f_cols = list(m.feature_names_in_)
                X_hist = hist_df.reindex(columns=f_cols, fill_value=0)
                hist_preds = m.predict(X_hist)
                historical_pred[target] = [round(float(p), 3) for p in hist_preds]
                historical_actual[target] = [round(float(a), 3) for a in hist_df[target]]

    return {
        "province": province,
        "steps": steps,
        "predictions": predictions,
        "historical_dates": historical_dates,
        "historical_actual": historical_actual,
        "historical_pred": historical_pred,
    }
