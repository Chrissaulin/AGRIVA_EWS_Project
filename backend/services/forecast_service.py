"""
Forecast service.
Contains execute_batch_forecast (BackgroundTasks job) and batch orchestration.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd
from sqlalchemy import case, func
from sqlalchemy.orm import Session

import ml.loader as ml_loader
from ml.predictor import EWSPredictor
from repositories.forecast_repo import (
    ForecastBatchRepository,
    ForecastFeatureRepository,
    EWSForecastResultRepository,
    ForecastMonthlyRepository,
)
from repositories.province_repo import ProvinceRepository
from services.ews_service import resolve_pipeline
from services.feature_engineering import get_province_dataframe_with_features


def _to_monthly_records(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["year"], row["month"])].append(row)

    monthly: list[dict] = []
    for (year, month), group in sorted(grouped.items()):
        latest_date = max(row["forecast_date"] for row in group)
        monthly.append({
            "month": month,
            "year": year,
            "forecast_date": latest_date,
            "rainfall": sum(row["rainfall"] or 0 for row in group) / max(len(group), 1),
            "spi_3_months": sum(row["spi_3_months"] or 0 for row in group) / max(len(group), 1),
            "temperature": sum(row["temperature"] or 0 for row in group) / max(len(group), 1),
            "wsi": sum(row["wsi"] or 0 for row in group) / max(len(group), 1),
            "solar_radiation": sum(row["solar_radiation"] or 0 for row in group) / max(len(group), 1),
            "soil_moisture": sum(row["soil_moisture"] or 0 for row in group) / max(len(group), 1),
            "fpar": sum(row["fpar"] or 0 for row in group) / max(len(group), 1),
            "fpar_zscore": sum(row["fpar_zscore"] or 0 for row in group) / max(len(group), 1),
            "ews_label": max({label: group.count(label) for label in {row["ews_label"] for row in group}}.items(), key=lambda item: item[1])[0],
            "ews_probability": sum(row["ews_probability"] for row in group) / max(len(group), 1),
            "dekad_count": len(group),
        })
    return monthly


def execute_batch_forecast(batch_id: int, months_ahead: int | None = None) -> None:
    from database import SessionLocal

    db = SessionLocal()
    batch = db.query(models.ForecastBatch).filter(models.ForecastBatch.id == batch_id).first()
    if not batch:
        db.close()
        return

    if months_ahead is None:
        months_ahead = batch.months_ahead

    monthly_repo = ForecastMonthlyRepository(db)

    batch.status = "running"
    db.commit()

    try:
        if ml_loader.forecast_model is None or ml_loader.ews_pipeline is None:
            raise RuntimeError(
                "Models not loaded. Ensure classifier/forecaster exist in models_output."
            )

        provinces = db.query(models.Province).all()
        steps = months_ahead * 3

        total_processed = 0
        for prov in provinces:
            cluster_id = prov.cluster_wilayah
            if cluster_id not in ml_loader.forecast_model:
                continue

            cluster_models = ml_loader.forecast_model[cluster_id]
            df_prov = get_province_dataframe_with_features(prov.name, db)
            if df_prov.empty:
                continue

            prov_data = df_prov.sort_values("date").tail(100).copy()
            dekad_records: list[dict] = []

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
                        pred_val = float(m.predict(X_pred)[0])
                        pred_dict[target] = pred_val
                        new_row[target] = pred_val

                rainfall = pred_dict.get("Rainfall")
                spi_3_months = pred_dict.get("SPI - 3 months")
                temperature = pred_dict.get("Temperature")
                wsi = pred_dict.get("Water Satisfaction Index (WSI)")
                solar_radiation = pred_dict.get("Solar Radiation")
                soil_moisture = pred_dict.get("Soil Moisture (gapfilled historical time series)")
                fpar = pred_dict.get("FPAR")
                fpar_zscore = pred_dict.get("FPAR - zscore")

                feat_record = models.ForecastFeature(
                    province_id=prov.id,
                    batch_id=batch_id,
                    forecast_date=next_date.date(),
                    rainfall=rainfall,
                    spi_3_months=spi_3_months,
                    temperature=temperature,
                    wsi=wsi,
                    solar_radiation=solar_radiation,
                    soil_moisture=soil_moisture,
                    fpar=fpar,
                    fpar_zscore=fpar_zscore,
                    month=next_date.month,
                    year=next_date.year,
                    dekad_id=new_row["dekad_id"],
                )
                db.add(feat_record)
                db.flush()

                pipeline, threshold = resolve_pipeline(cluster_id)
                f_cols = list(pipeline.feature_names_in_)
                features_df = pd.DataFrame([new_row]).reindex(columns=f_cols, fill_value=0)
                ews_res = predict_ews(cluster_id, features_df, threshold=threshold)

                res_repo = EWSForecastResultRepository(db)
                res_repo.create(
                    province_id=prov.id,
                    batch_id=batch_id,
                    forecast_date=next_date.date(),
                    cluster_used=cluster_id,
                    ews_label=ews_res["ews_label"],
                    ews_probability=ews_res["ews_probability"],
                )

                dekad_records.append({
                    "province_id": prov.id,
                    "batch_id": batch_id,
                    "forecast_date": next_date.date(),
                    "month": next_date.month,
                    "year": next_date.year,
                    "rainfall": rainfall,
                    "spi_3_months": spi_3_months,
                    "temperature": temperature,
                    "wsi": wsi,
                    "solar_radiation": solar_radiation,
                    "soil_moisture": soil_moisture,
                    "fpar": fpar,
                    "fpar_zscore": fpar_zscore,
                    "ews_label": ews_res["ews_label"],
                    "ews_probability": ews_res["ews_probability"],
                })

                prov_data = pd.concat([prov_data, pd.DataFrame([new_row])], ignore_index=True)

            monthly_records = _to_monthly_records(dekad_records)
            for rec in monthly_records:
                rec["province_id"] = prov.id
                rec["batch_id"] = batch_id
                monthly_repo.upsert(**rec)

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
