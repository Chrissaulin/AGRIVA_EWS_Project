import os
import sys
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in python path so we can import from database and models
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database import engine, Base, get_db
from models import Province, HistoricalMetric

RAW_DATA_DIR = "/app/raw_data"

def run_etl():
    print("Starting ETL Process...")
    
    # 1. Initialize Tables
    Base.metadata.create_all(bind=engine)
    
    # Check idempotency
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM historical_metric"))
        count = result.scalar()
        if count > 0:
            print(f"ETL already run. Found {count} records in historical_metric. Exiting.")
            return

    # 2. Load CSVs
    csv1_path = os.path.join(RAW_DATA_DIR, "asap_indonesia_master_2001.csv")
    csv2_path = os.path.join(RAW_DATA_DIR, "data_master_clustered.csv")
    csv3_path = os.path.join(RAW_DATA_DIR, "data_forecast_ready.csv")

    print(f"Reading CSV 1: {csv1_path}")
    df1 = pd.read_csv(csv1_path)
    print(f"Reading CSV 2: {csv2_path}")
    df2 = pd.read_csv(csv2_path)
    print(f"Reading CSV 3: {csv3_path}")
    df3 = pd.read_csv(csv3_path)

    # Convert date to datetime
    df1['date'] = pd.to_datetime(df1['date'])
    df2['date'] = pd.to_datetime(df2['date'])
    df3['date'] = pd.to_datetime(df3['date'])

    # Merge on date and region_name
    print("Merging DataFrames...")
    # Base is df1 because it has raw climate features
    merged = pd.merge(df1, df2[['date', 'region_name', 'Cluster_Wilayah', 'target_biner', 'month_extracted']], on=['date', 'region_name'], how='left')
    merged = pd.merge(merged, df3[['date', 'region_name', 'year', 'dayofyear', 'weekofyear']], on=['date', 'region_name'], how='left')

    # Impute missing values
    print("Imputing missing values...")
    merged.sort_values(by=['region_name', 'date'], inplace=True)
    merged.ffill(inplace=True)
    merged.bfill(inplace=True)

    # Populate Provinces
    print("Populating Province table...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Get unique provinces and their clusters
    province_info = merged[['region_name', 'Cluster_Wilayah']].drop_duplicates(subset=['region_name'])
    province_map = {}
    for _, row in province_info.iterrows():
        prov_name = row['region_name']
        cluster = int(row['Cluster_Wilayah']) if pd.notnull(row['Cluster_Wilayah']) else None
        
        # Insert or get
        prov = db.query(Province).filter(Province.name == prov_name).first()
        if not prov:
            prov = Province(name=prov_name, cluster_wilayah=cluster)
            db.add(prov)
            db.commit()
            db.refresh(prov)
        province_map[prov_name] = prov.id

    # Transform for HistoricalMetric
    print("Transforming HistoricalMetrics...")
    rename_map = {
        'Rainfall': 'rainfall',
        'SPI - 3 months': 'spi_3_months',
        'Temperature': 'temperature',
        'Water Satisfaction Index (WSI)': 'wsi',
        'Solar Radiation': 'solar_radiation',
        'Soil Moisture (gapfilled historical time series)': 'soil_moisture',
        'FPAR': 'fpar',
        'FPAR - zscore': 'fpar_zscore'
    }
    
    # We only need specific columns for HistoricalMetric
    final_cols = ['date', 'region_name'] + list(rename_map.keys()) + ['target_biner', 'month_extracted', 'year', 'dayofyear', 'weekofyear']
    metrics_df = merged[final_cols].rename(columns=rename_map).copy()
    
    metrics_df['province_id'] = metrics_df['region_name'].map(province_map)
    metrics_df.drop(columns=['region_name'], inplace=True)

    # Convert pandas datetime back to string or let SQLAlchemy handle it
    # metrics_df['date'] = metrics_df['date'].dt.date

    # Drop duplicates in case of overlaps in original data
    metrics_df.drop_duplicates(subset=['province_id', 'date'], inplace=True)

    # Insert into database using chunking
    print("Loading data into historical_metric...")
    metrics_df.to_sql('historical_metric', con=engine, if_exists='append', index=False, chunksize=10000)
    
    print("ETL Seeder Script completed successfully!")

if __name__ == "__main__":
    run_etl()
