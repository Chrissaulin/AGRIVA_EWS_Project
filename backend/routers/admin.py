from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

import models
from database import get_db
from services.forecast_service import execute_batch_forecast


router = APIRouter()


@router.post("/api/admin/run-forecast")
def run_forecast_batch(req, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from schemas.forecast import RunForecastRequest

    if not isinstance(req, RunForecastRequest):
        req = RunForecastRequest(**req)

    batch = models.ForecastBatch(
        triggered_by="api",
        months_ahead=req.months_ahead,
        status="pending"
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(execute_batch_forecast, batch.id)
    return {"message": "Forecast batch job queued", "batch_id": batch.id}


@router.get("/api/batches")
def get_batches(db: Session = Depends(get_db)):
    batches = db.query(models.ForecastBatch).order_by(models.ForecastBatch.created_at.desc()).all()
    return [{
        "id": b.id,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "triggered_by": b.triggered_by,
        "months_ahead": b.months_ahead,
        "status": b.status,
        "total_provinces": b.total_provinces,
        "notes": b.notes
    } for b in batches]
