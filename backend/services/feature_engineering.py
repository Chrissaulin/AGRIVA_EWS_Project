"""
Feature engineering service.
Uses repositories for data access.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from repositories.metrics_repo import HistoricalMetricRepository


def get_province_dataframe_with_features(
    province_name: str,
    db: Session,
) -> "pandas.DataFrame":
    from repositories.metrics_repo import HistoricalMetricRepository
    import pandas as pd

    repo = HistoricalMetricRepository(db)
    metrics = repo.get_by_province(province_name)
    return HistoricalMetricRepository.build_dataframe(metrics, province_name)
