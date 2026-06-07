"""
Forecast service.
Contains execute_batch_forecast (BackgroundTasks job) and batch orchestration.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from ml.loader import ews_pipeline, forecast_model
from ml.predictor import EWSPredictor
from repositories.forecast_repo import (
    ForecastBatchRepository,
    ForecastFeatureRepository,
    EWSForecastResultRepository,
)
from repositories.province_repo import ProvinceRepository
from services.ews_service import resolve_pipeline
from services.feature_engineering import get_province_dataframe_with_features


def execute_batch_forecast(batch_id: int) -> None:
    from database import SessionLocal

    db = SessionLocal()
    batch = db.query(models.ForecastBatch).filter(models.ForecastBatch.id == batch_id).first()
    if not batch:
        db.close()
        return

    batch.status = "running"
    db.commit()

    try:
        if forecast_model is None or ews_pipeline is None:
            raise RuntimeError(
                "Models not loaded. Ensure classifier/forecaster exist in models_output."
            )

        provinces = db.query(models.Province).all()
        steps = batch.months_ahead * 3

        total_processed = 0
        for prov in provinces:
            cluster_id = prov.cluster_wilayah
            if cluster_id not in forecast_model:
                continue

            cluster_models = forecast_model[cluster_id]
            df_prov = get_province_dataframe_with_features(prov.name, db)
            if df_prov.empty:
                continue

            prov_data = df_prov.sort_values("date").tail(100).copy()

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

                lag_targets = config.TARGET_FORECAST_COLS
                for t in lag_targets:
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

                pred_dict = {}
                for target in config.TARGET_FORECAST_COLS:
                    if target in cluster_models:
                        m = cluster_models[target]
                        f_cols = list(m.feature_names_in_)
                        X_pred = pd.DataFrame([new_row]).reindex(columns=f_cols, fill_value=0)
                        pred_val = float(m.predict(X_pred)[0])
                        pred_dict[target] = pred_val
                        new_row[target] = pred_val

                feat_record = models.ForecastFeature(
                    province_id=prov.id,
                    batch_id=batch_id,
                    forecast_date=next_date.date(),
                    rainfall=pred_dict.get("Rainfall"),
                    spi_3_months=pred_dict.get("SPI - 3 months"),
                    temperature=pred_dict.get("Temperature"),
                    wsi=pred_dict.get("Water Satisfaction Index (WSI)"),
                    solar_radiation=pred_dict.get("Solar Radiation"),
                    soil_moisture=pred_dict.get("Soil Moisture (gapfilled historical time series)"),
                    fpar=pred_dict.get("FPAR"),
                    fpar_zscore=pred_dict.get("FPAR - zscore"),
                    month=next_date.month,
                    year=next_date.year,
                    dekad_id=new_row["dekad_id"],
                )
                db.add(feat_record)
                db.flush()

                # EWS prediction on the forecasted features
                pipeline, threshold = resolve_pipeline(cluster_id)
                f_cols = list(pipeline.feature_names_in_)
                features_df = pd.DataFrame([new_row]).reindex(columns=f_cols, fill_value=0)
                ews_res = EWSPredictor.predict(pipeline, features_df, threshold=threshold)

                res_repo = EWSForecastResultRepository(db)
                res_repo.create(
                    province_id=prov.id,
                    batch_id=batch_id,
                    forecast_date=next_date.date(),
                    cluster_used=cluster_id,
                    ews_label=ews_res["ews_label"],
                    ews_probability=ews_res["ews_probability"],
                )

                prov_data = pd.concat([prov_data, pd.DataFrame([new_row])], ignore_index=True)

            total_processed += 1

        batch.status = "done"
        batch.total_provinces = total_processed
        db.commit()
        print(
            f"[OK] Forecast batch {batch_id} completed. "
            f"Processed {total_processed} provinces."
        )
    except Exception as e:
        db.rollback()
        batch.status = "failed"
        batch.notes = str(e)
        db.commit()
        print(f"[ERROR] Forecast batch {batch_id} failed: {e}")
    finally:
        db.close()
