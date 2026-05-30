import os
import sys
import pandas as pd
from sqlalchemy import text

# Add the project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine, Base, SessionLocal
from app.models import MasterClusteredRecord, ForecastReadyRecord

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "01_dapur_jupyter", "data"))
MASTER_CSV = os.path.join(DATA_PATH, "data_master_clustered.csv")
FORECAST_CSV = os.path.join(DATA_PATH, "data_forecast_ready.csv")

# Direct column mapping lookup
COL_MAPPING = {
    'date': 'date',
    'region_name': 'region_name',
    'Rainfall': 'rainfall',
    'SPI - 3 months': 'spi_3m',
    'Temperature': 'temperature',
    'Water Satisfaction Index (WSI)': 'wsi',
    'Solar Radiation': 'solar_radiation',
    'Soil Moisture (gapfilled historical time series)': 'soil_moisture',
    'FPAR': 'fpar',
    'FPAR - zscore': 'fpar_zscore',
    'asap0_id': 'asap0_id',
    'asap1_id': 'asap1_id',
    'month': 'month',
    'day': 'day',
    'dekad_id': 'dekad_id',
    'target_ews': 'target_ews',
    'Cluster_Wilayah': 'cluster_wilayah',
    'month_extracted': 'month_extracted',
    'year': 'year',
    'dayofyear': 'dayofyear',
    'weekofyear': 'weekofyear'
}

def translate_columns(df):
    """Translate CSV column headers into database ORM names."""
    new_cols = []
    for col in df.columns:
        if col in COL_MAPPING:
            new_cols.append(COL_MAPPING[col])
        elif col.startswith("region_name_"):
            # Replace spaces, dots, dashes with underscores
            mapped = col.replace(" ", "_").replace(".", "_").replace("-", "_")
            # Keep special end-underscores for Kalimantan S. -> region_name_Kalimantan_S_ etc
            new_cols.append(mapped)
        else:
            new_cols.append(col)
    df.columns = new_cols
    return df

def seed():
    print("=== STARTING DATABASE SEEDING PROCESS ===")
    
    # 1. Create all schemas
    print("Verifying database tables and schemas...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if already seeded
        m_count = db.query(MasterClusteredRecord).count()
        f_count = db.query(ForecastReadyRecord).count()
        
        if m_count > 0 and f_count > 0:
            print(f"Database already populated! (Master: {m_count} rows, Forecast: {f_count} rows)")
            print("Skipping seeding process.")
            return
            
        # 2. Seed Master Clustered Table
        if m_count == 0:
            print(f"Reading master clustered records from: {MASTER_CSV}")
            if not os.path.exists(MASTER_CSV):
                print(f"ERROR: File not found at {MASTER_CSV}")
                return
                
            df_master = pd.read_csv(MASTER_CSV)
            print("Applying column transformations for master clustered data...")
            df_master = translate_columns(df_master)
            
            # Convert date to string format for SQLite/PG compliance
            df_master['date'] = pd.to_datetime(df_master['date']).dt.strftime('%Y-%m-%d')
            
            print(f"Seeding {len(df_master)} records into master_clustered_data...")
            # We use pandas to_sql for maximum insertion speed (bulk seeding)
            df_master.to_sql(
                name="master_clustered_data",
                con=engine,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000
            )
            print("Master clustered seeding completed successfully!")
            
        # 3. Seed Forecast Ready Table
        if f_count == 0:
            print(f"Reading forecast-ready records from: {FORECAST_CSV}")
            if not os.path.exists(FORECAST_CSV):
                print(f"ERROR: File not found at {FORECAST_CSV}")
                return
                
            df_forecast = pd.read_csv(FORECAST_CSV)
            print("Applying column transformations for forecast-ready data...")
            df_forecast = translate_columns(df_forecast)
            
            # Convert date to string
            df_forecast['date'] = pd.to_datetime(df_forecast['date']).dt.strftime('%Y-%m-%d')
            
            print(f"Seeding {len(df_forecast)} records into forecast_ready_data...")
            df_forecast.to_sql(
                name="forecast_ready_data",
                con=engine,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000
            )
            print("Forecast-ready seeding completed successfully!")
            
        print("=== DATABASE SEEDING COMPLETED SUCCESSFULLY ===")
    except Exception as e:
        print(f"=== SEEDING ERROR ENCOUNTERED ===")
        print(str(e))
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
