"""
Forecast repository.
ForecastBatch, ForecastFeature, EWSForecastResult queries.
"""
from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session

import models


class ForecastBatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, months_ahead: int, triggered_by: str = "api") -> models.ForecastBatch:
        batch = models.ForecastBatch(
            triggered_by=triggered_by,
            months_ahead=months_ahead,
            status="pending",
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_latest_done(self) -> models.ForecastBatch | None:
        return (
            self.db.query(models.ForecastBatch)
            .filter(models.ForecastBatch.status == "done")
            .order_by(models.ForecastBatch.created_at.desc())
            .first()
        )

    def get_all(self) -> list[models.ForecastBatch]:
        return self.db.query(models.ForecastBatch).order_by(models.ForecastBatch.created_at.desc()).all()


class ForecastFeatureRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> models.ForecastFeature:
        record = models.ForecastFeature(**kwargs)
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_batch(self, batch_id: int) -> list[models.ForecastFeature]:
        return (
            self.db.query(models.ForecastFeature)
            .filter(models.ForecastFeature.batch_id == batch_id)
            .all()
        )


class EWSForecastResultRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> models.EWSForecastResult:
        record = models.EWSForecastResult(**kwargs)
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_batch(self, batch_id: int) -> list[models.EWSForecastResult]:
        return (
            self.db.query(models.EWSForecastResult)
            .filter(models.EWSForecastResult.batch_id == batch_id)
            .all()
        )


class ForecastMonthlyRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, **kwargs) -> models.ForecastMonthly:
        """Merge to avoid duplicate key errors on re-runs."""
        record = models.ForecastMonthly(**kwargs)
        self.db.merge(record)
        self.db.flush()
        return record

    def get_by_batch_and_period(self, batch_id: int, month: int = None, year: int = None) -> list[models.ForecastMonthly]:
        query = self.db.query(models.ForecastMonthly).filter(
            models.ForecastMonthly.batch_id == batch_id
        )
        if month is not None:
            query = query.filter(models.ForecastMonthly.month == month)
        if year is not None:
            query = query.filter(models.ForecastMonthly.year == year)
        return query.all()

    def get_latest_by_province(self, province_id: int, batch_id: int):
        return (
            self.db.query(models.ForecastMonthly)
            .filter(
                models.ForecastMonthly.province_id == province_id,
                models.ForecastMonthly.batch_id == batch_id,
            )
            .order_by(models.ForecastMonthly.year.asc(), models.ForecastMonthly.month.asc())
            .all()
        )
