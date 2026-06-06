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
