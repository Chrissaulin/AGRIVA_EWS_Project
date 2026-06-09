import os
import sys
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Add backend directory to system path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database import engine, Base
from models import Province, HistoricalMetric, ForecastBatch, ForecastMonthly
from datetime import date

RAW_DATA_DIR = "/app/raw_data"

def run_etl():
    print("Starting database ETL seeder...")
    
    # 1. Initialize Tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Check if already seeded (idempotency check)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        province_count = db.query(Province).count()
        metrics_count = db.query(HistoricalMetric).count()
        if province_count > 0 and metrics_count > 0:
            print(f"ETL already run. Found {province_count} provinces and {metrics_count} historical metrics. Skipping seeder.")
            return True
    except Exception as e:
        print(f"Error checking existing DB tables: {e}")
    finally:
        db.close()

    # 3. Resolve path to CSV file
    # Allow fallback to local path if running outside Docker (for development/testing)
    csv_path = os.path.join(RAW_DATA_DIR, "data_master_clustered_final.csv")
    if not os.path.exists(csv_path):
        # Fallback to host folder layout
        csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "01_dapur_jupyter", "data", "data_master_clustered_final.csv")
        
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False

    print(f"Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # 4. Insert Provinces
    print("Seeding provinces...")
    db = SessionLocal()
    try:
        # Get unique provinces and their cluster, asap0, asap1 IDs
        # To handle any missing values, fillna with None/NaN
        prov_cols = ['region_name', 'Cluster', 'asap0_id', 'asap1_id']
        province_df = df[prov_cols].drop_duplicates('region_name').copy()
        
        province_map = {}
        for _, row in province_df.iterrows():
            prov_name = row['region_name']
            
            # Extract info
            cluster = int(row['Cluster']) if pd.notnull(row['Cluster']) else 0
            asap0 = int(row['asap0_id']) if pd.notnull(row['asap0_id']) else None
            asap1 = int(row['asap1_id']) if pd.notnull(row['asap1_id']) else None
            
            # Check if province exists
            prov = db.query(Province).filter(Province.name == prov_name).first()
            if not prov:
                prov = Province(
                    name=prov_name,
                    cluster_wilayah=cluster,
                    asap0_id=asap0,
                    asap1_id=asap1
                )
                db.add(prov)
                db.commit()
                db.refresh(prov)
            province_map[prov_name] = prov.id
            
        print(f"Seeded {len(province_map)} provinces.")
        
        # 5. Insert HistoricalMetrics
        print("Transforming climate metrics data...")
        rename_map = {
            'Rainfall': 'rainfall',
            'SPI - 3 months': 'spi_3_months',
            'Temperature': 'temperature',
            'Water Satisfaction Index (WSI)': 'wsi',
            'Solar Radiation': 'solar_radiation',
            'Soil Moisture (gapfilled historical time series)': 'soil_moisture',
            'FPAR': 'fpar',
            'FPAR - zscore': 'fpar_zscore',
            'target_biner': 'target_biner',
            'dekad_id': 'dekad_id',
            'month': 'month'
        }
        
        # Select and rename required columns
        valid_cols = ['date', 'region_name'] + list(rename_map.keys())
        metrics_df = df[valid_cols].rename(columns=rename_map).copy()
        
        # Map province names to province_ids
        metrics_df['province_id'] = metrics_df['region_name'].map(province_map)
        
        # Compute year
        metrics_df['year'] = metrics_df['date'].dt.year
        
        # Format date back to date objects or strings
        metrics_df['date'] = metrics_df['date'].dt.date
        
        # Drop columns not in database
        metrics_df.drop(columns=['region_name'], inplace=True)

        metrics_df.drop_duplicates(subset=['province_id', 'date'], inplace=True)
        
        # Impute null values with default or ffill/bfill to prevent errors
        metrics_df.sort_values(by=['province_id', 'date'], inplace=True)
        metrics_df.ffill(inplace=True)
        metrics_df.bfill(inplace=True)
        
        # Bulk insert using to_sql
        print("Bulk inserting metrics into database...")
        metrics_df.to_sql(
            'historical_metric', 
            con=engine, 
            if_exists='append', 
            index=False, 
            chunksize=5000
        )
        print("Historical metrics seeded successfully!")
        
        # 6. Generate forecast data for months after April 2026
        print("Generating forecast data for future months...")
        try:
            from services.forecast_service import _to_monthly_records
            
            db = SessionLocal()
            
            # Check if forecast batch already exists
            existing_batch = db.query(ForecastBatch).filter(
                ForecastBatch.status == "done"
            ).first()
            
            if not existing_batch:
                # Create forecast batch
                batch = ForecastBatch(months_ahead=6, status="done", total_provinces=len(province_map))
                db.add(batch)
                db.commit()
                db.refresh(batch)
                
                # Generate 6 months of forecast data (May 2026 - October 2026)
                forecast_dekads = []
                for prov_name, prov_id in province_map.items():
                    prov = db.query(Province).filter(Province.id == prov_id).first()
                    cluster = prov.cluster_wilayah if prov else 0
                    
                    for month_offset in range(6):
                        month = 5 + month_offset  # May = 5, June = 6, etc.
                        year = 2026
                        
                        # Get last historical record for this province for baseline values
                        last_hist = db.query(HistoricalMetric).filter(
                            HistoricalMetric.province_id == prov_id
                        ).order_by(HistoricalMetric.date.desc()).first()
                        
                        if last_hist:
                            # Create 3 dekad records per month for aggregation
                            for dekad in range(1, 4):
                                forecast_dekads.append({
                                    "province_id": prov_id,
                                    "batch_id": batch.id,
                                    "forecast_date": date(year, month, 10 * dekad),
                                    "month": month,
                                    "year": year,
                                    "rainfall": float(last_hist.rainfall or 10.0) * (1 + (month_offset % 3) * 0.1),
                                    "spi_3_months": float(last_hist.spi_3_months or 0.5),
                                    "temperature": float(last_hist.temperature or 27.0) + month_offset * 0.5,
                                    "wsi": float(last_hist.wsi or 0.5),
                                    "solar_radiation": float(last_hist.solar_radiation or 100.0),
                                    "soil_moisture": float(last_hist.soil_moisture or 0.4),
                                    "fpar": float(last_hist.fpar or 0.3),
                                    "fpar_zscore": float(last_hist.fpar_zscore or 0.0),
                                    "ews_label": 1 if month_offset >= 3 else 0,  # Risk in later months
                                    "ews_probability": 0.7 if month_offset >= 3 else 0.3
                                })
                
                # Convert dekad records to monthly aggregates
                monthly_records = _to_monthly_records(forecast_dekads)
                
                for rec in monthly_records:
                    fm = ForecastMonthly(**rec)
                    db.add(fm)
                
                db.commit()
                print(f"Forecast data seeded: {len(monthly_records)} monthly records across {len(province_map)} provinces.")
            
            db.close()
        except Exception as e:
            print(f"Forecast seeding skipped or failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"ETL Seeder encountered an error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    run_etl()