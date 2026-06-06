from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

import models
from database import get_db

router = APIRouter()


@router.post("/api/simulate")
def simulate_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = file.file.read()
        text_data = contents.decode("utf-8")
        lines = [l.strip() for l in text_data.split("\n") if l.strip()]
        row_count = len(lines) - 1 if len(lines) > 0 else 0

        session_record = models.SimulationSession(
            source_filename=file.filename,
            row_count=row_count,
            notes="CSV simulation uploaded via API."
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)

        return {
            "session_id": session_record.id,
            "filename": file.filename,
            "row_count": row_count,
            "status": "logged"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")
