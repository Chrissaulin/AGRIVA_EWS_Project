from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session
import numpy as np

import models
from database import get_db

from services.scaling_service import load_scaler_stats
import core.config as config


router = APIRouter()


@router.get("/api/map/filters")
def map_filters(db: Session = Depends(get_db)):
    years = sorted([int(y[0]) for y in db.query(models.HistoricalMetric.year).distinct().all() if y[0] is not None])
    months = list(range(1, 13))
    return {"years": years, "months": months}


@router.get("/api/map/data")
def map_data(year: Optional[str] = None, month: Optional[str] = None,
             mode: str = "historical", db: Session = Depends(get_db)):
    year_int = int(year) if year and year != "" else None
    month_int = int(month) if month and month != "" else None
    
    if mode == "forecast":
        return _map_data_forecast(db, year_int, month_int)
    
    # Try historical first
    result = _map_data_historical(year, month, db)
    
    # Auto-fallback to forecast if no historical data
    if not result.get("provinces"):
        result = _map_data_forecast(db, year_int, month_int)
    
    return result


def _map_data_historical(year: Optional[str], month: Optional[str], db: Session):
    year_val = None if (year is None or year == "") else int(year)
    month_val = None if (month is None or month == "") else int(month)

    if year_val is None or month_val is None:
        latest = db.query(models.HistoricalMetric).order_by(models.HistoricalMetric.year.desc(), models.HistoricalMetric.month.desc()).first()
        if latest:
            year_val = year_val or latest.year
            month_val = month_val or latest.month
        else:
            year_val = 2026
            month_val = 4

    metrics = (
        db.query(models.HistoricalMetric)
        .join(models.Province)
        .filter(models.HistoricalMetric.year == year_val)
        .filter(models.HistoricalMetric.month == month_val)
        .all()
    )

    if not metrics:
        return {"provinces": [], "message": "No data found for the selected period."}

    # Group results by province name
    prov_groups = {}
    for m in metrics:
        p_name = m.province.name
        if p_name not in prov_groups:
            prov_groups[p_name] = []
        prov_groups[p_name].append(m)

    province_names = [p[0] for p in db.query(models.Province.name).order_by(models.Province.name.asc()).all()]

    result = []
    for prov in province_names:
        m_list = prov_groups.get(prov, [])
        if not m_list:
            continue

        has_risk = int(max([m.target_biner or 0 for m in m_list]))
        risk_count = sum([1 for m in m_list if m.target_biner == 1])
        total_count = len(m_list)

        avg_rainfall = round(float(np.mean([m.rainfall for m in m_list if m.rainfall is not None])), 2) if m_list else 0.0
        avg_temp = round(float(np.mean([m.temperature for m in m_list if m.temperature is not None])), 2) if m_list else 0.0
        avg_spi = round(float(np.mean([m.spi_3_months for m in m_list if m.spi_3_months is not None])), 2) if m_list else 0.0

        # Unscale values from z-scores to real-world for display
        try:
            scaler_stats = load_scaler_stats()
            if avg_rainfall != 0.0 and 'Rainfall' in scaler_stats:
                avg_rainfall = round(avg_rainfall * scaler_stats['Rainfall']['scale'] + scaler_stats['Rainfall']['center'], 2)
            if avg_temp != 0.0 and 'Temperature' in scaler_stats:
                avg_temp = round(avg_temp * scaler_stats['Temperature']['scale'] + scaler_stats['Temperature']['center'], 2)
        except Exception:
            pass

        cluster = db.query(models.Province.cluster_wilayah).filter(models.Province.name == prov).scalar()

        result.append({
            "province": prov,
            "warning": "Berisiko" if has_risk == 1 else "Aman",
            "warning_code": has_risk,
            "risk_records": risk_count,
            "total_records": total_count,
            "cluster": int(cluster) if cluster is not None else -1,
            "avg_rainfall": avg_rainfall,
            "avg_temperature": avg_temp,
            "avg_spi": avg_spi,
        })

    return {"provinces": result, "year": year_val, "month": month_val}


def _map_data_forecast(db: Session, year: int = None, month: int = None):
    latest_batch = db.query(models.ForecastBatch).filter(
        models.ForecastBatch.status == "done"
    ).order_by(models.ForecastBatch.created_at.desc()).first()

    if not latest_batch:
        return {"provinces": [], "message": "No forecast data available."}

    query = (
        db.query(models.Province, models.ForecastMonthly)
        .join(models.ForecastMonthly, models.ForecastMonthly.province_id == models.Province.id)
        .filter(models.ForecastMonthly.batch_id == latest_batch.id)
    )
    if year is not None:
        query = query.filter(models.ForecastMonthly.year == year)
    if month is not None:
        query = query.filter(models.ForecastMonthly.month == month)
    metrics = query.order_by(models.ForecastMonthly.id.asc()).all()

    if not metrics:
        return {"provinces": [], "message": "No forecast data available for the selected period."}

    result = []
    for prov, fm in metrics:
        result.append({
            "province": prov.name,
            "warning": "Berisiko" if fm.ews_label == 1 else "Aman",
            "warning_code": fm.ews_label,
            "cluster": prov.cluster_wilayah,
            "avg_rainfall": round(float(fm.rainfall), 2) if fm.rainfall is not None else 0.0,
            "avg_temperature": round(float(fm.temperature), 2) if fm.temperature is not None else 0.0,
            "avg_spi": round(float(fm.spi_3_months), 2) if fm.spi_3_months is not None else 0.0,
            "forecast_month": fm.month,
            "forecast_year": fm.year,
            "forecast_date": fm.forecast_date.strftime('%Y-%m-%d'),
        })

    return {"provinces": result, "batch_id": latest_batch.id, "created_at": latest_batch.created_at}
