import os
import sys
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Add backend directory to system path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database import engine, Base
from models import Province, HistoricalMetric

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
        prov_cols = ['region_name', 'Cluster_Wilayah', 'asap0_id', 'asap1_id']
        province_df = df[prov_cols].drop_duplicates('region_name').copy()
        
        province_map = {}
        for _, row in province_df.iterrows():
            prov_name = row['region_name']
            
            # Extract info
            cluster = int(row['Cluster_Wilayah']) if pd.notnull(row['Cluster_Wilayah']) else 0
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
        return True
        
    except Exception as e:
        print(f"ETL Seeder encountered an error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    run_etl()