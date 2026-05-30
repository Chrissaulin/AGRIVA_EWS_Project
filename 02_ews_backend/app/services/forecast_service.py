import datetime
import pandas as pd
from sqlalchemy.orm import Session
from app.models import ForecastReadyRecord, MasterClusteredRecord
from app.schemas import ForecastRequest, ForecastResponse, ForecastResponseRecord

def increment_dekad(current_date: datetime.date) -> datetime.date:
    """
    Menambahkan tanggal sebanyak satu dekad (10 hari).
    Menyesuaikan kalender ASAP di mana dekad berulang pada tanggal 1, 11, atau 21 setiap bulan.
    """
    day = current_date.day
    month = current_date.month
    year = current_date.year
    
    if day == 1:
        new_day = 11
    elif day == 11:
        new_day = 21
    else: # day == 21
        new_day = 1
        month += 1
        if month > 12:
            month = 1
            year += 1
            
    return datetime.date(year, month, new_day)

def generate_forecast(
    request: ForecastRequest, 
    db: Session, 
    encoder, 
    forecast_model
) -> ForecastResponse:
    """
    Menghasilkan ramalan multi-step Auto-Regressive menggunakan model multi-output XGBoost
    yang sudah dimuat dan data historis terbaru dari database sebagai nilai awal lag.
    """
    province = request.region_name
    steps = request.steps
    
    # 1. Ambil 3 data historis terakhir untuk wilayah tersebut sebagai seed lag awal
    historical_records = db.query(MasterClusteredRecord).filter(
        MasterClusteredRecord.region_name == province
    ).order_by(MasterClusteredRecord.date.desc()).limit(3).all()
    
    if not historical_records:
        raise ValueError(f"Tidak ditemukan catatan historis di database untuk provinsi: {province}")
        
    # Karena data diurutkan secara descending (tanggal terbaru di depan):
    # index 0: Lag 1 (terbaru), index 1: Lag 2, index 2: Lag 3 (terlama)
    lag_rainfall = [r.rainfall for r in historical_records]
    lag_temp = [r.temperature for r in historical_records]
    lag_sm = [r.soil_moisture for r in historical_records]
    
    # Toleransi kegagalan jika data DB kurang dari 3 (fallback safety)
    while len(lag_rainfall) < 3:
        lag_rainfall.append(lag_rainfall[-1] if lag_rainfall else 50.0)
        lag_temp.append(lag_temp[-1] if lag_temp else 25.0)
        lag_sm.append(lag_sm[-1] if lag_sm else 0.3)
        
    # Ambil tanggal terakhir untuk perhitungan dekad berikutnya
    last_date = historical_records[0].date
    
    # 2. Bangun representasi one-hot encoding untuk provinsi yang dipilih
    # Sesuai dengan 33 fitur one-hot provinsi yang dipelajari model
    encoded_array = encoder.transform([[province]])
    encoded_list = encoded_array.tolist()[0]
    prov_cols = list(encoder.get_feature_names_out(['region_name']))
    
    forecasts = []
    current_date = last_date
    
    # 3. Loop Auto-Regressive untuk melangkah ke depan (multi-step)
    for step in range(1, steps + 1):
        current_date = increment_dekad(current_date)
        
        # Ekstrak fitur-fitur waktu (temporal features)
        year = current_date.year
        month = current_date.month
        day = current_date.day
        dayofyear = current_date.timetuple().tm_yday
        weekofyear = int(current_date.isocalendar()[1])
        
        # Susun feature dictionary
        feat_dict = {
            'year': year,
            'month': month,
            'day': day,
            'dayofyear': dayofyear,
            'weekofyear': weekofyear
        }
        
        # Masukkan fitur one-hot provinsi
        for col, val in zip(prov_cols, encoded_list):
            feat_dict[col] = val
            
        # Masukkan fitur lag weather
        feat_dict['Rainfall_lag_1'] = lag_rainfall[0]
        feat_dict['Rainfall_lag_2'] = lag_rainfall[1]
        feat_dict['Rainfall_lag_3'] = lag_rainfall[2]
        
        feat_dict['Temperature_lag_1'] = lag_temp[0]
        feat_dict['Temperature_lag_2'] = lag_temp[1]
        feat_dict['Temperature_lag_3'] = lag_temp[2]
        
        feat_dict['Soil Moisture (gapfilled historical time series)_lag_1'] = lag_sm[0]
        feat_dict['Soil Moisture (gapfilled historical time series)_lag_2'] = lag_sm[1]
        feat_dict['Soil Moisture (gapfilled historical time series)_lag_3'] = lag_sm[2]
        
        # Konversi ke DataFrame dan pastikan urutan kolom sesuai dengan urutan latihan model
        X = pd.DataFrame([feat_dict])
        X_cols = [
            'year', 'month', 'day', 'dayofyear', 'weekofyear'
        ] + prov_cols + [
            'Rainfall_lag_1', 'Rainfall_lag_2', 'Rainfall_lag_3',
            'Temperature_lag_1', 'Temperature_lag_2', 'Temperature_lag_3',
            'Soil Moisture (gapfilled historical time series)_lag_1',
            'Soil Moisture (gapfilled historical time series)_lag_2',
            'Soil Moisture (gapfilled historical time series)_lag_3'
        ]
        X = X[X_cols]
        
        # Eksekusi prediksi dengan XGBoost multi-output regressor
        preds = forecast_model.predict(X)[0]
        
        # Batasi output prediksi agar realistis (misal curah hujan tidak boleh minus)
        pred_rainfall = max(0.0, float(preds[0]))
        pred_spi = float(preds[1])
        pred_temp = float(preds[2])
        pred_wsi = min(100.0, max(0.0, float(preds[3])))
        pred_solar = max(0.0, float(preds[4]))
        pred_sm_val = min(1.0, max(0.0, float(preds[5])))
        pred_fpar = max(0.0, float(preds[6]))
        pred_fpar_z = float(preds[7])
        
        # Simpan hasil peramalan langkah ini
        forecasts.append(ForecastResponseRecord(
            step=step,
            date=current_date,
            rainfall=round(pred_rainfall, 2),
            spi_3m=round(pred_spi, 3),
            temperature=round(pred_temp, 2),
            wsi=round(pred_wsi, 2),
            solar_radiation=round(pred_solar, 1),
            soil_moisture=round(pred_sm_val, 4),
            fpar=round(pred_fpar, 2),
            fpar_zscore=round(pred_fpar_z, 3)
        ))
        
        # Geser (roll over) nilai lag curah hujan, suhu, dan kelembaban tanah untuk langkah berikutnya
        lag_rainfall = [pred_rainfall, lag_rainfall[0], lag_rainfall[1]]
        lag_temp = [pred_temp, lag_temp[0], lag_temp[1]]
        lag_sm = [pred_sm_val, lag_sm[0], lag_sm[1]]
        
    return ForecastResponse(
        region_name=province,
        forecasts=forecasts
    )
