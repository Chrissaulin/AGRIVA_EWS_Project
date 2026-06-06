from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

from database import engine, get_db, SessionLocal, init_db
import models
from scripts.etl_seeder import run_etl

import shared
import core.config as config
from routers.eda import router as eda_router
from routers.map import router as map_router
from routers.forecast import router as forecast_router
from routers.predict import router as predict_router
from routers.admin import router as admin_router
from routers.simulate import router as simulate_router

app = FastAPI(title="AGRIVA EWS API", version="2.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def load_resources():
    print("Initializing Database tables...")
    try:
        init_db(retries=5, delay=2)
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")

    try:
        db = SessionLocal()
        prov_count = db.query(models.Province).count()
        metrics_count = db.query(models.HistoricalMetric).count()
        db.close()

        if prov_count == 0 or metrics_count == 0:
            print("[INFO] Database tables are empty. Seeding database...")
            run_etl()
        else:
            print(f"[INFO] Database populated with {prov_count} provinces and {metrics_count} metrics.")
    except Exception as e:
        print(f"[ERROR] Failed checking database state: {e}")

    classifier_path = os.path.join(config.MODEL_DIR, "agriva_master_classifier.pkl")
    if os.path.exists(classifier_path):
        shared.ews_pipeline = __import__('joblib').load(classifier_path)
        print("[OK] EWS Pipeline loaded successfully!")
    else:
        print(f"[WARN] EWS Pipeline not found at {classifier_path}")

    forecast_path = os.path.join(config.MODEL_DIR, "agriva_master_forecaster.pkl")
    if os.path.exists(forecast_path):
        shared.forecast_model = __import__('joblib').load(forecast_path)
        print("[OK] Forecast Model loaded successfully!")
    else:
        print(f"[WARN] Forecast Model not found at {forecast_path}")

    try:
        db = SessionLocal()
        provinces = db.query(models.Province).order_by(models.Province.name.asc()).all()
        config.PROVINCES_LIST = [p.name for p in provinces]
        config.CLUSTER_MAP = {p.name: p.cluster_wilayah for p in provinces}
        shared.PROVINCES_LIST = config.PROVINCES_LIST
        shared.CLUSTER_MAP = config.CLUSTER_MAP
        db.close()
        print(f"[OK] Pre-loaded {len(config.PROVINCES_LIST)} provinces from database.")
    except Exception as e:
        print(f"[ERROR] Failed to load provinces list from DB: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(eda_router)
app.include_router(map_router)
app.include_router(forecast_router)
app.include_router(predict_router)
app.include_router(admin_router)
app.include_router(simulate_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
