from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

import models
from database import get_db
import core.config as config
from services.predict_service import predict_ews_endpoint


router = APIRouter()


@router.get("/api/predict/provinces")
def predict_provinces(db: Session = Depends(get_db)):
    provinces = db.query(models.Province).order_by(models.Province.name.asc()).all()
    return {
        "provinces": [
            {"name": p.name, "cluster": p.cluster_wilayah}
            for p in provinces
        ]
    }


@router.post("/api/predict/ews")
def predict_ews(req, db: Session = Depends(get_db)):
    from schemas.predict import PredictionRequest

    if not isinstance(req, PredictionRequest):
        req = PredictionRequest(**req)

    try:
        return predict_ews_endpoint(req, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
