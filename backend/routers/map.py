from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session
import numpy as np

import models
from database import get_db

import core.config as config


router = APIRouter()


@router.get("/api/map/filters")
def map_filters(db: Session = Depends(get_db)):
    years = sorted([int(y[0]) for y in db.query(models.HistoricalMetric.year).distinct().all() if y[0] is not None])
    months = list(range(1, 13))
    return {"years": years, "months": months}


@router.get("/api/map/data")
def map_data(year: Optional[str] = None, month: Optional[str] = None, db: Session = Depends(get_db)):
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

    result = []
    for prov in config.PROVINCES_LIST:
        m_list = prov_groups.get(prov, [])
        if not m_list:
            continue

        has_risk = int(max([m.target_biner or 0 for m in m_list]))
        risk_count = sum([1 for m in m_list if m.target_biner == 1])
        total_count = len(m_list)

        avg_rainfall = round(float(np.mean([m.rainfall for m in m_list if m.rainfall is not None])), 2) if m_list else 0.0
        avg_temp = round(float(np.mean([m.temperature for m in m_list if m.temperature is not None])), 2) if m_list else 0.0
        avg_spi = round(float(np.mean([m.spi_3_months for m in m_list if m.spi_3_months is not None])), 2) if m_list else 0.0

        result.append({
            "province": prov,
            "warning": "Berisiko" if has_risk == 1 else "Aman",
            "warning_code": has_risk,
            "risk_records": risk_count,
            "total_records": total_count,
            "cluster": config.CLUSTER_MAP.get(prov, -1),
            "avg_rainfall": avg_rainfall,
            "avg_temperature": avg_temp,
            "avg_spi": avg_spi,
        })

    return {"provinces": result, "year": year_val, "month": month_val}
