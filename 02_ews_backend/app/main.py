import os
import joblib
import pandas as pd
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.database import engine, get_db, Base
from app.models import MasterClusteredRecord
from app.schemas import (
    RegionResponse, 
    MetricsSummary, 
    TrendRecord, 
    SimulationInput, 
    SimulationResponse, 
    ForecastRequest, 
    ForecastResponse
)
from app.services.predict_service import predict_ews_risk
from app.services.forecast_service import generate_forecast

# 1. Menentukan path lokasi model dan data CSV secara dinamis
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAPUR_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "01_dapur_jupyter"))
MODELS_DIR = os.path.join(DAPUR_DIR, "models_output")
MASTER_CSV = os.path.join(DAPUR_DIR, "data", "data_master_clustered.csv")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager untuk memuat model machine learning secara efisien ke memori (RAM)
    hanya satu kali saat server melakukan start-up (Cold Start), menghindari overhead disk I/O.
    """
    print("=== FASTAPI STARTUP: MEMUAT MODEL ML KE RAM ===")
    app.state.models = {}
    
    # Memuat Encoder Provinsi
    encoder_path = os.path.join(MODELS_DIR, "encoder_provinsi.pkl")
    if os.path.exists(encoder_path):
        app.state.models["encoder_provinsi"] = joblib.load(encoder_path)
        print("-> encoder_provinsi.pkl berhasil dimuat.")
    else:
        print(f"-> WARNING: {encoder_path} tidak ditemukan!")
        
    # Memuat Model Peramalan Global (XGBRegressor)
    forecast_path = os.path.join(MODELS_DIR, "model_forecast_global.pkl")
    if os.path.exists(forecast_path):
        app.state.models["model_forecast_global"] = joblib.load(forecast_path)
        print("-> model_forecast_global.pkl berhasil dimuat.")
    else:
        print(f"-> WARNING: {forecast_path} tidak ditemukan!")
        
    # Memuat Model Klasifikasi Biner EWS untuk masing-masing Cluster 0, 1, dan 2
    for c in range(3):
        model_name = f"pipeline_ews_biner_cluster_{c}.pkl"
        model_path = os.path.join(MODELS_DIR, model_name)
        if os.path.exists(model_path):
            app.state.models[f"pipeline_cluster_{c}"] = joblib.load(model_path)
            print(f"-> {model_name} berhasil dimuat.")
        else:
            print(f"-> WARNING: {model_path} tidak ditemukan!")
            
    # 2. Mengambil pemetaan wilayah-ke-cluster secara dinamis dari CSV Master
    print("Mengekstraksi relasi provinsi ke cluster secara dinamis...")
    if os.path.exists(MASTER_CSV):
        df_master = pd.read_csv(MASTER_CSV)
        # Menghubungkan region_name ke Cluster_Wilayah pertama yang ditemukan
        app.state.region_to_cluster = (
            df_master.groupby("region_name")["Cluster_Wilayah"]
            .first()
            .to_dict()
        )
        print(f"-> Berhasil memetakan {len(app.state.region_to_cluster)} provinsi ke clusternya.")
    else:
        print(f"-> WARNING: {MASTER_CSV} tidak ditemukan! Menggunakan pemetaan kosong.")
        app.state.region_to_cluster = {}
        
    # Pastikan database terisi otomatis jika menggunakan SQLite fallback
    print("Memverifikasi skema database lokal...")
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # Bersihkan memori saat aplikasi mati
    app.state.models.clear()
    app.state.region_to_cluster.clear()
    print("=== FASTAPI SHUTDOWN: LAYANAN BERHENTI ===")


app = FastAPI(
    title="AGRIVA Early Warning System (EWS) API",
    description="Backend API untuk sistem peringatan dini ketahanan pangan Indonesia.",
    version="1.0.0",
    lifespan=lifespan
)

# 3. Konfigurasi Kebijakan CORS untuk akses frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mengizinkan akses dari semua host untuk development lokal
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "status": "Online",
        "message": "Selamat datang di AGRIVA Early Warning System (EWS) API Service.",
        "docs_url": "/docs"
    }


@app.get("/api/regions", response_model=List[RegionResponse])
def get_regions(db: Session = Depends(get_db)):
    """Mengambil seluruh daftar 33 provinsi dan indeks clusternya."""
    if not hasattr(app.state, "region_to_cluster") or not app.state.region_to_cluster:
        raise HTTPException(status_code=500, detail="Data pemetaan cluster belum dimuat.")
        
    # Ambil status risiko terbaru untuk setiap region
    latest_records = db.query(
        MasterClusteredRecord.region_name, 
        MasterClusteredRecord.target_ews
    ).order_by(MasterClusteredRecord.date.desc()).all()
    
    risk_map = {}
    for r in latest_records:
        if r.region_name not in risk_map:
            risk_map[r.region_name] = 1 if r.target_ews and r.target_ews > 0 else 0
            
    res = []
    for region, cluster in app.state.region_to_cluster.items():
        risk = risk_map.get(region, 0)
        res.append(RegionResponse(region_name=region, cluster_wilayah=cluster, risk_status=risk))
    return sorted(res, key=lambda x: x.region_name)


@app.get("/api/summary", response_model=MetricsSummary)
def get_summary(
    region_name: Optional[str] = None,
    cluster_wilayah: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Mengambil data agregat rata-rata indikator iklim dan tanaman pangan
    serta total peringatan bahaya EWS.
    """
    query = db.query(
        func.avg(MasterClusteredRecord.rainfall).label("avg_rainfall"),
        func.avg(MasterClusteredRecord.spi_3m).label("avg_spi_3m"),
        func.avg(MasterClusteredRecord.temperature).label("avg_temperature"),
        func.avg(MasterClusteredRecord.wsi).label("avg_wsi"),
        func.avg(MasterClusteredRecord.soil_moisture).label("avg_soil_moisture"),
        func.avg(MasterClusteredRecord.fpar).label("avg_fpar"),
        func.sum(case((MasterClusteredRecord.target_ews > 0, 1), else_=0)).label("total_alerts")
    )
    
    if region_name:
        query = query.filter(MasterClusteredRecord.region_name == region_name)
    if cluster_wilayah is not None:
        query = query.filter(MasterClusteredRecord.cluster_wilayah == cluster_wilayah)
        
    res = query.first()
    if not res or res.avg_rainfall is None:
        return MetricsSummary(
            region_name=region_name,
            cluster_wilayah=cluster_wilayah,
            avg_rainfall=0.0,
            avg_spi_3m=0.0,
            avg_temperature=0.0,
            avg_wsi=0.0,
            avg_soil_moisture=0.0,
            avg_fpar=0.0,
            total_alerts=0
        )
        
    return MetricsSummary(
        region_name=region_name or "Indonesia (Semua)",
        cluster_wilayah=cluster_wilayah,
        avg_rainfall=round(res.avg_rainfall, 2),
        avg_spi_3m=round(res.avg_spi_3m, 3),
        avg_temperature=round(res.avg_temperature, 2),
        avg_wsi=round(res.avg_wsi, 2),
        avg_soil_moisture=round(res.avg_soil_moisture, 4),
        avg_fpar=round(res.avg_fpar, 2),
        total_alerts=int(res.total_alerts or 0)
    )


@app.get("/api/trends/{region}", response_model=List[TrendRecord])
def get_trends(region: str, db: Session = Depends(get_db)):
    """Mengambil 120 rekaman historis runtun waktu (sekitar ~3 tahun terakhir) untuk grafik tren wilayah."""
    records = db.query(MasterClusteredRecord).filter(
        MasterClusteredRecord.region_name == region
    ).order_by(MasterClusteredRecord.date.asc()).all()
    
    if not records:
        raise HTTPException(status_code=404, detail=f"Catatan historis tidak ditemukan untuk provinsi: {region}")
        
    # Membatasi output ke 120 catatan terakhir agar respons cepat dan visual grafik tetap informatif
    return records[-120:]


@app.post("/api/simulate/predict", response_model=SimulationResponse)
def simulate_predict(input_data: SimulationInput):
    """
    Menerima input parameter kustom pertanian dari frontend, mencari clusternya secara dinamis,
    dan mengevaluasi status bahaya EWS terhadap ambang batas recall optimal model.
    """
    if "encoder_provinsi" not in app.state.models:
        raise HTTPException(status_code=500, detail="Model-model ML belum berhasil dimuat di server.")
        
    try:
        response = predict_ews_risk(
            input_data=input_data,
            region_to_cluster=app.state.region_to_cluster,
            models=app.state.models
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal melakukan simulasi EWS: {str(e)}")


@app.post("/api/simulate/forecast", response_model=ForecastResponse)
async def simulate_forecast(request: Request, db: Session = Depends(get_db)):
    """
    Melakukan peramalan meteorologi dan vegetasi multi-dekad kedepan menggunakan
    mekanisme Auto-Regressive XGBoost (rolling lag rollover).
    """
    try:
        payload = await request.json()
        print(f"DEBUG INCOMING FORECAST PAYLOAD: {payload}")
        request_obj = ForecastRequest(**payload)
    except Exception as e:
        print(f"Validation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid payload format: {str(e)}")

    if "model_forecast_global" not in app.state.models or "encoder_provinsi" not in app.state.models:
        raise HTTPException(status_code=500, detail="Model peramalan global belum dimuat di server.")
        
    try:
        response = generate_forecast(
            request=request_obj,
            db=db,
            encoder=app.state.models["encoder_provinsi"],
            forecast_model=app.state.models["model_forecast_global"]
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal memproses peramalan: {str(e)}")
