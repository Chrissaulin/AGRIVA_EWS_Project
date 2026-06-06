from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
import joblib
import pandas as pd
import numpy as np
import os

import models
from database import get_db

import core.config as config


router = APIRouter()


@router.get("/api/eda/dashboard")
def eda_dashboard(
    province: Optional[str] = "All",
    year: Optional[str] = "All",
    dist_feature: Optional[str] = "Soil Moisture (gapfilled historical time series)",
    db: Session = Depends(get_db)
):
    query = db.query(models.HistoricalMetric).join(models.Province)

    if province != "All" and province in config.PROVINCES_LIST:
        query = query.filter(models.Province.name == province)

    if year != "All" and year.isdigit():
        query = query.filter(models.HistoricalMetric.year == int(year))

    results = query.all()
    if not results:
        return {"error": "No data found for selected filters"}

    # Build a DataFrame dynamically from the query results
    data_list = []
    for r in results:
        data_list.append({
            'region_name': r.province.name,
            'Rainfall': r.rainfall,
            'SPI - 3 months': r.spi_3_months,
            'Temperature': r.temperature,
            'Water Satisfaction Index (WSI)': r.wsi,
            'Solar Radiation': r.solar_radiation,
            'Soil Moisture (gapfilled historical time series)': r.soil_moisture,
            'FPAR': r.fpar,
            'FPAR - zscore': r.fpar_zscore,
            'target_biner': r.target_biner,
            'month_extracted': r.month if r.month else 1,
            'year': r.year
        })
    df = pd.DataFrame(data_list)

    # Calculate statistics
    avg_rain = float(df['Rainfall'].mean()) if not df.empty else 0
    avg_temp = float(df['Temperature'].mean()) if not df.empty else 0

    mode_target = df['target_biner'].mode()
    dominant_status = "Berisiko" if not mode_target.empty and mode_target.iloc[0] == 1 else "Aman"
    max_temp = float(df['Temperature'].max()) if not df.empty else 0

    aman_count = int((df['target_biner'] == 0).sum())
    berisiko_count = int((df['target_biner'] == 1).sum())

    # Dynamic feature histogram
    if dist_feature and dist_feature in df.columns:
        hist_counts, hist_bins = np.histogram(df[dist_feature].dropna(), bins=10)
        feature_dist = {
            "labels": [f"{round(hist_bins[i], 2)}-{round(hist_bins[i+1], 2)}" for i in range(len(hist_counts))],
            "data": hist_counts.tolist()
        }
    else:
        feature_dist = {"labels": [], "data": []}

    # Time Series: Rainfall vs WSI per month
    ts_data = df.groupby('month_extracted')[['Rainfall', 'Water Satisfaction Index (WSI)']].mean().reset_index()
    time_series = {
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "rainfall": [float(ts_data[ts_data['month_extracted'] == m]['Rainfall'].mean()) if m in ts_data['month_extracted'].values else 0 for m in range(1, 13)],
        "wsi": [float(ts_data[ts_data['month_extracted'] == m]['Water Satisfaction Index (WSI)'].mean()) if m in ts_data['month_extracted'].values else 0 for m in range(1, 13)]
    }

    # Radar Chart: 7 Indicators (scaled using local min-max stats to fit 0-100)
    radar_features = ['Rainfall', 'SPI - 3 months', 'Temperature', 'Water Satisfaction Index (WSI)', 'Solar Radiation', 'Soil Moisture (gapfilled historical time series)', 'FPAR']
    radar_data = []

    for f in radar_features:
        f_max = df[f].max()
        f_min = df[f].min()
        f_val = df[f].mean()
        scaled = ((f_val - f_min) / (f_max - f_min)) * 100 if f_max != f_min else 0
        radar_data.append(round(float(scaled), 2))

    # Scatter plot data
    scatter_df = df.sample(n=min(300, len(df)), random_state=42)[['Rainfall', 'Soil Moisture (gapfilled historical time series)', 'target_biner']].dropna()
    scatter_data = {
        "aman": [{"x": float(row['Rainfall']), "y": float(row['Soil Moisture (gapfilled historical time series)'])} for _, row in scatter_df[scatter_df['target_biner'] == 0].iterrows()],
        "berisiko": [{"x": float(row['Rainfall']), "y": float(row['Soil Moisture (gapfilled historical time series)'])} for _, row in scatter_df[scatter_df['target_biner'] == 1].iterrows()]
    }

    # Data Table Summary
    table_features = radar_features + ['FPAR - zscore']
    if province == "All":
        table_df = df.groupby('region_name')[table_features + ['target_biner']].mean().reset_index()
        table_df['target_biner'] = df.groupby('region_name')['target_biner'].sum().reset_index()['target_biner']
        table_df = table_df.head(15).round(2)
        table_data = table_df.rename(columns={'region_name': 'Kategori'}).to_dict(orient='records')
    else:
        table_df = df.groupby('year')[table_features + ['target_biner']].mean().reset_index()
        table_df['target_biner'] = df.groupby('year')['target_biner'].sum().reset_index()['target_biner']
        table_df = table_df.head(15).round(2)
        table_data = table_df.rename(columns={'year': 'Kategori'}).to_dict(orient='records')

    years_list = sorted([int(y[0]) for y in db.query(models.HistoricalMetric.year).distinct().all() if y[0] is not None])

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
        "years": years_list,
        "provinces": config.PROVINCES_LIST
    }


@router.get("/api/classification/dashboard")
def get_classification_dashboard(cluster: str = "all"):
    classifier_path = os.path.join(config.MODEL_DIR, "agriva_master_classifier.pkl")
    if not os.path.exists(classifier_path):
        return {"error": "Classification XGBoost pipeline not found."}

    models_dict = joblib.load(classifier_path)

    # Notebook Gold Standard Metrics
    notebook_metrics = {
        "0": {"tp": 218, "fn": 41, "fp": 145, "tn": 427, "precision": 0.60, "recall": 0.84, "f1": 0.70, "roc": 0.88},
        "1": {"tp": 81, "fn": 28, "fp": 88, "tn": 192, "precision": 0.48, "recall": 0.74, "f1": 0.58, "roc": 0.81},
        "2": {"tp": 72, "fn": 30, "fp": 134, "tn": 40, "precision": 0.35, "recall": 0.71, "f1": 0.47, "roc": 0.74},
    }

    global_tp = sum(v["tp"] for v in notebook_metrics.values())
    global_fn = sum(v["fn"] for v in notebook_metrics.values())
    global_fp = sum(v["fp"] for v in notebook_metrics.values())
    global_tn = sum(v["tn"] for v in notebook_metrics.values())

    global_recall = global_tp / (global_tp + global_fn)
    global_precision = global_tp / (global_tp + global_fp)
    global_f1 = 2 * (global_precision * global_recall) / (global_precision + global_recall)
    global_roc = sum(v["roc"] for v in notebook_metrics.values()) / 3

    if cluster == "all":
        tp, fn, fp, tn = global_tp, global_fn, global_fp, global_tn
        recall, f1, roc_auc = global_recall, global_f1, global_roc
        opt_thresh = sum([models_dict[i].get('threshold_siaga', 0.5) if type(models_dict[i]) == dict else 0.5 for i in range(3)])/3
    else:
        m = notebook_metrics[cluster]
        tp, fn, fp, tn = m["tp"], m["fn"], m["fp"], m["tn"]
        recall, f1, roc_auc = m["recall"], m["f1"], m["roc"]

        cluster_dict = models_dict[int(cluster)]
        opt_thresh = cluster_dict.get('threshold_siaga', 0.5) if type(cluster_dict) == dict else 0.5

    cm = [[tn, fp], [fn, tp]]

    features = ['Rainfall', 'SPI - 3 months', 'Temperature', 'Water Satisfaction Index (WSI)', 'Solar Radiation', 'Soil Moisture (gapfilled historical time series)', 'FPAR', 'FPAR - zscore', 'month', 'day', 'dekad_id', 'Rainfall_lag_1', 'Rainfall_lag_3', 'Rainfall_lag_6', 'Temperature_lag_1', 'Temperature_lag_3', 'Temperature_lag_6', 'Soil Moisture (gapfilled historical time series)_lag_1', 'Soil Moisture (gapfilled historical time series)_lag_3', 'Soil Moisture (gapfilled historical time series)_lag_6', 'Water Satisfaction Index (WSI)_lag_1', 'Water Satisfaction Index (WSI)_lag_3', 'Water Satisfaction Index (WSI)_lag_6', 'Rainfall_roll_mean_30', 'Rainfall_roll_std_30', 'Rainfall_roll_mean_90', 'Rainfall_roll_std_90', 'Soil Moisture (gapfilled historical time series)_roll_mean_30', 'Soil Moisture (gapfilled historical time series)_roll_std_30', 'Soil Moisture (gapfilled historical time series)_roll_mean_90', 'Soil Moisture (gapfilled historical time series)_roll_std_90', 'Water Satisfaction Index (WSI)_roll_mean_30', 'Water Satisfaction Index (WSI)_roll_std_30', 'Water Satisfaction Index (WSI)_roll_mean_90', 'Water Satisfaction Index (WSI)_roll_std_90']

    # Feature importances dynamically calculated from model
    if cluster != "all":
        cluster_dict = models_dict[int(cluster)]
        model_obj = cluster_dict['model_xgboost'] if type(cluster_dict) == dict else cluster_dict
        importances = model_obj.feature_importances_
    else:
        imp_0 = models_dict[0]['model_xgboost'].feature_importances_ if type(models_dict[0]) == dict else models_dict[0].feature_importances_
        imp_1 = models_dict[1]['model_xgboost'].feature_importances_ if type(models_dict[1]) == dict else models_dict[1].feature_importances_
        imp_2 = models_dict[2]['model_xgboost'].feature_importances_ if type(models_dict[2]) == dict else models_dict[2].feature_importances_
        importances = (imp_0 + imp_1 + imp_2) / 3

    indices = np.argsort(importances)[::-1][:10]
    fi_labels = [features[i] for i in indices]
    fi_data = importances[indices].tolist()

    # Dummy PR curve data
    pr_data = [{"x": float(r/20.0), "y": float(np.exp(-r/5.0))} for r in range(0, 21)]

    # Table data
    table_data = []
    for c_id in [0, 1, 2]:
        m = notebook_metrics[str(c_id)]
        table_data.append({
            "cluster": f"Klaster {c_id}",
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"]
        })

    return {
        "kpis": {
            "recall": f"{recall * 100:.1f}%",
            "f1": f"{f1 * 100:.1f}%",
            "roc_auc": round(float(roc_auc), 3),
            "optimal_threshold": round(float(opt_thresh), 2)
        },
        "confusion_matrix": cm,
        "feature_importance": {
            "labels": fi_labels,
            "data": [round(float(x), 4) for x in fi_data]
        },
        "class_proportion": [tn+fp, tp+fn],
        "pr_curve": pr_data,
        "table": table_data
    }
