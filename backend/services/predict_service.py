"""
Prediction service.
Shared predict_ews and forecast_predict logic used by routers.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

import core.config as config
import ml.loader as ml_loader
import models
from repositories.province_repo import ProvinceRepository
from repositories.simulation_repo import SimulationSessionRepository
from services.ews_service import resolve_pipeline, predict_ews
from services.feature_engineering import get_province_dataframe_with_features
from services.scaling_service import scale_input, unscale_output
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

    # User provides real-world values - scale them before model input
    user_values = {
        "Rainfall": request.Rainfall,
        "SPI - 3 months": request.SPI_3_months,
        "Temperature": request.Temperature,
        "Water Satisfaction Index (WSI)": request.WSI,
        "Solar Radiation": request.Solar_Radiation,
        "Soil Moisture (gapfilled historical time series)": request.Soil_Moisture,
        "FPAR": request.FPAR,
        "FPAR - zscore": request.FPAR_zscore,
    }
    
    # Scale only the features that have scaler stats (excludes month_extracted)
    scaled_values = scale_input(user_values)  # Use only features with stats

    last_row = df_prov.sort_values("date").iloc[-1].copy()
    last_row["month_extracted"] = request.month_extracted if hasattr(request, 'month_extracted') else 6
    
    # Apply scaled values to features that were actually scaled
    for feat, scaled_val in scaled_values.items():
        if feat in last_row.index:
            last_row[feat] = scaled_val

    if ml_loader.ews_pipeline is None:
        raise RuntimeError("EWS Master Pipeline not loaded.")

    ews_result = predict_ews(
        cluster_id=cluster_id,
        features_df=pd.DataFrame([last_row]).fillna(0),
        threshold=None,
        pipeline_override=ml_loader.ews_pipeline if not isinstance(ml_loader.ews_pipeline, dict) else None,
    )
    threshold = ews_result["threshold"]

    try:
        repo = ProvinceRepository(db)
        prov_obj = repo.get_by_name(request.province)
        session_repo = SimulationSessionRepository(db)
        session_record = session_repo.create(
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
    import numpy as np

    forecast_model = ml_loader.forecast_model
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

    forecast_model_bundle = forecast_model.get(cluster_id)
    if forecast_model_bundle is None:
        raise ValueError(f"Forecast model for cluster {cluster_id} not found.")

    # Extract forecaster and schema from bundle (saved format: forecaster_object, lag_features_schema, target_features_schema)
    forecaster = forecast_model_bundle.get("forecaster_object")
    lag_cols = forecast_model_bundle.get("lag_features_schema", [])
    target_cols = forecast_model_bundle.get("target_features_schema", config.TARGET_FORECAST_COLS)

    if forecaster is None:
        raise RuntimeError(f"Forecaster object missing for cluster {cluster_id}.")

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

        for t in target_cols:
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

        # Prepare features for MultiOutputRegressor
        X_pred = pd.DataFrame([new_row]).reindex(columns=lag_cols, fill_value=0)
        pred_vals = forecaster.predict(X_pred)[0]  # MultiOutputRegressor returns 2D array

        pred_dict = {target_cols[i]: float(pred_vals[i]) for i in range(len(target_cols))}

        # Apply predictions back to the row for recursive forecasting
        for target in target_cols:
            if target in pred_dict:
                new_row[target] = pred_dict[target]

        # Unscale the prediction for display (scaled -> real-world values)
        pred_unscaled = unscale_output(pred_dict, target_cols)

        predictions.append(
            {
                "date": next_date.strftime("%Y-%m-%d"),
                "step": step + 1,
                "predicted": pred_unscaled,
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
        # Prepare historical features
        X_hist = hist_df.reindex(columns=lag_cols, fill_value=0)
        hist_preds = forecaster.predict(X_hist)

        for target_idx, target in enumerate(target_cols):
            hist_pred_vals = [float(p[target_idx]) for p in hist_preds]
            # Predictions are in scaled form - unscale for display
            hist_pred_unscaled = unscale_output(
                {target: [round(p, 3) for p in hist_pred_vals]}, [target]
            )
            historical_pred[target] = hist_pred_unscaled.get(target, [])
            # Historical actuals are z-scores in DB - unscale for display
            historical_actual[target] = unscale_output(
                {target: [float(a) for a in hist_df[target].values]}, [target]
            ).get(target, [0.0])

    return {
        "province": province,
        "steps": steps,
        "predictions": predictions,
        "historical_dates": historical_dates,
        "historical_actual": historical_actual,
        "historical_pred": historical_pred,
    }
