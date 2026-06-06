"""
HistoricalMetric repository.
Contains DataFrame builder for feature engineering.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

import models


class HistoricalMetricRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_province(self, province_name: str) -> list[models.HistoricalMetric]:
        return (
            self.db.query(models.HistoricalMetric)
            .join(models.Province)
            .filter(models.Province.name == province_name)
            .order_by(models.HistoricalMetric.date.asc())
            .all()
        )

    def get_by_year(self, province_name: str, year: int) -> list[models.HistoricalMetric]:
        return (
            self.db.query(models.HistoricalMetric)
            .join(models.Province)
            .filter(models.Province.name == province_name)
            .filter(models.HistoricalMetric.year == year)
            .all()
        )

    def get_latest(self, limit: int = 108) -> list[models.HistoricalMetric]:
        return (
            self.db.query(models.HistoricalMetric)
            .order_by(models.HistoricalMetric.date.desc())
            .limit(limit)
            .all()
        )

    def get_by_cluster(self, cluster_id: int) -> list[models.HistoricalMetric]:
        return (
            self.db.query(models.HistoricalMetric)
            .join(models.Province)
            .filter(models.Province.cluster_wilayah == cluster_id)
            .all()
        )

    @staticmethod
    def build_dataframe(metrics: list[models.HistoricalMetric], province_name: str) -> pd.DataFrame:
        """Convert ORM rows to feature-engineered DataFrame."""
        if not metrics:
            return pd.DataFrame()

        data_list: list[dict[str, Any]] = []
        for m in metrics:
            dt = pd.to_datetime(m.date)
            data_list.append({
                "date": dt,
                "region_name": province_name,
                "Rainfall": m.rainfall,
                "SPI - 3 months": m.spi_3_months,
                "Temperature": m.temperature,
                "Water Satisfaction Index (WSI)": m.wsi,
                "Solar Radiation": m.solar_radiation,
                "Soil Moisture (gapfilled historical time series)": m.soil_moisture,
                "FPAR": m.fpar,
                "FPAR - zscore": m.fpar_zscore,
                "target_biner": m.target_biner,
                "month": m.month,
                "day": dt.day,
                "dekad_id": m.dekad_id,
                "year": m.year,
                "dayofyear": dt.dayofyear,
                "weekofyear": dt.isocalendar()[1],
                "month_extracted": m.month if m.month is not None else 1,
            })
        df = pd.DataFrame(data_list)

        lag_targets = [
            "Rainfall",
            "Temperature",
            "Soil Moisture (gapfilled historical time series)",
            "SPI - 3 months",
            "Water Satisfaction Index (WSI)",
            "Solar Radiation",
            "FPAR",
            "FPAR - zscore",
        ]
        for t in lag_targets:
            df[f"{t}_lag_1"] = df[t].shift(1)
            df[f"{t}_lag_3"] = df[t].shift(3)
            df[f"{t}_lag_6"] = df[t].shift(6)
            df[f"{t}_lag1"] = df[f"{t}_lag_1"]
            df[f"{t}_lag3"] = df[f"{t}_lag_3"]

        roll_targets = [
            "Rainfall",
            "Soil Moisture (gapfilled historical time series)",
            "Water Satisfaction Index (WSI)",
        ]
        for t in roll_targets:
            df[f"{t}_roll_mean_30"] = df[t].rolling(30, min_periods=1).mean()
            df[f"{t}_roll_std_30"] = df[t].rolling(30, min_periods=1).std().fillna(0)
            df[f"{t}_roll_mean_90"] = df[t].rolling(90, min_periods=1).mean()
            df[f"{t}_roll_std_90"] = df[t].rolling(90, min_periods=1).std().fillna(0)
            df[f"{t}_rollmean3"] = df[t].rolling(3, min_periods=1).mean()

        return df
