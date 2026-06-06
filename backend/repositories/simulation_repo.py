"""
Simulation repository.
SimulationSession queries.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

import models


class SimulationSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> models.SimulationSession:
        record = models.SimulationSession(**kwargs)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
