from sqlalchemy import Column, Integer, Float, String, Date, Index
from .database import Base

class MasterClusteredRecord(Base):
    """ORM representation of the historical clustered crop/weather dataset."""
    __tablename__ = "master_clustered_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    region_name = Column(String(100), nullable=False, index=True)
    
    # Climatological & Crop Indicators
    rainfall = Column(Float, nullable=True)
    spi_3m = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    wsi = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)
    fpar = Column(Float, nullable=True)
    fpar_zscore = Column(Float, nullable=True)
    
    # Metadata identifiers
    asap0_id = Column(Integer, nullable=True)
    asap1_id = Column(Integer, nullable=True)
    
    # Temporal markers
    month = Column(Integer, nullable=True)
    day = Column(Integer, nullable=True)
    dekad_id = Column(Integer, nullable=True)
    
    # EWS Outcome and Territory Cluster
    target_ews = Column(Integer, nullable=True)
    cluster_wilayah = Column(Integer, nullable=True, index=True)
    month_extracted = Column(Integer, nullable=True)

    # Performance Indexing
    __table_args__ = (
        Index("idx_master_region_date", "region_name", "date"),
    )


class ForecastReadyRecord(Base):
    """ORM representation of time-series processed forecasting features."""
    __tablename__ = "forecast_ready_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    region_name = Column(String(100), nullable=False, index=True)
    
    # Climatological & Crop Indicators
    rainfall = Column(Float, nullable=True)
    spi_3m = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    wsi = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)
    fpar = Column(Float, nullable=True)
    fpar_zscore = Column(Float, nullable=True)
    
    # Metadata identifiers
    asap0_id = Column(Integer, nullable=True)
    asap1_id = Column(Integer, nullable=True)
    
    # Temporal markers
    month = Column(Integer, nullable=True)
    day = Column(Integer, nullable=True)
    dekad_id = Column(Integer, nullable=True)
    
    # EWS Outcome and Territory Cluster
    target_ews = Column(Integer, nullable=True)
    cluster_wilayah = Column(Integer, nullable=True, index=True)
    month_extracted = Column(Integer, nullable=True)
    
    # Forecasting temporal indices
    year = Column(Integer, nullable=True)
    dayofyear = Column(Integer, nullable=True)
    weekofyear = Column(Integer, nullable=True)

    # Dynamic province one-hot encoding columns (represented as Floats or Integers)
    # We include all 33 province column mappings to support direct seed load matching the CSV structure
    region_name_Bali = Column(Float, default=0.0)
    region_name_Bangka_Belitung = Column(Float, default=0.0)
    region_name_Banten = Column(Float, default=0.0)
    region_name_Bengkulu = Column(Float, default=0.0)
    region_name_DI_Yogyakarta = Column(Float, default=0.0)
    region_name_Dki_Jakarta = Column(Float, default=0.0)
    region_name_Gorontalo = Column(Float, default=0.0)
    region_name_Jambi = Column(Float, default=0.0)
    region_name_Jawa_Barat = Column(Float, default=0.0)
    region_name_Jawa_Tengah = Column(Float, default=0.0)
    region_name_Jawa_Timur = Column(Float, default=0.0)
    region_name_Kalimantan_Barat = Column(Float, default=0.0)
    region_name_Kalimantan_S_ = Column(Float, default=0.0)
    region_name_Kalimantan_T_ = Column(Float, default=0.0)
    region_name_Kalimantan_Timur = Column(Float, default=0.0)
    region_name_Kepulauan_riau = Column(Float, default=0.0)
    region_name_Lampung = Column(Float, default=0.0)
    region_name_Maluku = Column(Float, default=0.0)
    region_name_Maluku_Utara = Column(Float, default=0.0)
    region_name_Nangroe_AD_ = Column(Float, default=0.0)
    region_name_Nusatenggara_B_ = Column(Float, default=0.0)
    region_name_Nusatenggara_T_ = Column(Float, default=0.0)
    region_name_Papua = Column(Float, default=0.0)
    region_name_Papua_Barat = Column(Float, default=0.0)
    region_name_Riau = Column(Float, default=0.0)
    region_name_Sulawesi_Barat = Column(Float, default=0.0)
    region_name_Sulawesi_Selatan = Column(Float, default=0.0)
    region_name_Sulawesi_Tengah = Column(Float, default=0.0)
    region_name_Sulawesi_Tengg_ = Column(Float, default=0.0)
    region_name_Sulawesi_Utara = Column(Float, default=0.0)
    region_name_Sumatera_Barat = Column(Float, default=0.0)
    region_name_Sumatera_Selatan = Column(Float, default=0.0)
    region_name_Sumatera_Utara = Column(Float, default=0.0)

    # Performance Indexing
    __table_args__ = (
        Index("idx_forecast_region_date", "region_name", "date"),
    )
