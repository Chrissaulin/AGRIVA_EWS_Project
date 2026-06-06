"""
Province repository.
Thin wrappers around Province queries.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

import models


class ProvinceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[models.Province]:
        return self.db.query(models.Province).order_by(models.Province.name.asc()).all()

    def get_by_name(self, name: str) -> models.Province | None:
        return self.db.query(models.Province).filter(models.Province.name == name).first()

    def count(self) -> int:
        return self.db.query(models.Province).count()
