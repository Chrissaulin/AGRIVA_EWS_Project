from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class Province(Base):
    __tablename__ = "province"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    cluster_wilayah = Column(Integer, nullable=True)
    # Relationship to historical metrics
    metrics = relationship("HistoricalMetric", back_populates="province")

class HistoricalMetric(Base):
    __tablename__ = "historical_metric"
    id = Column(Integer, primary_key=True, index=True)
    province_id = Column(Integer, ForeignKey("province.id"), nullable=False)
    date = Column(Date, nullable=False)
    rainfall = Column(Float)
    spi_3_months = Column(Float)
    temperature = Column(Float)
    wsi = Column(Float)
    solar_radiation = Column(Float)
    soil_moisture = Column(Float)
    fpar = Column(Float)
    fpar_zscore = Column(Float)
    target_biner = Column(Integer)
    month_extracted = Column(Integer)
    year = Column(Integer)
    dayofyear = Column(Integer)
    weekofyear = Column(Integer)
    # Ensure one record per province per date
    __table_args__ = (UniqueConstraint('province_id', 'date', name='_province_date_uc'),)
    province = relationship("Province", back_populates="metrics")

class ForecastRecord(Base):
    __tablename__ = "forecast_record"
    id = Column(Integer, primary_key=True, index=True)
    province_id = Column(Integer, ForeignKey("province.id"), nullable=False)
    date = Column(Date, nullable=False)
    rainfall = Column(Float)
    spi_3_months = Column(Float)
    temperature = Column(Float)
    wsi = Column(Float)
    solar_radiation = Column(Float)
    soil_moisture = Column(Float)
    fpar = Column(Float)
    fpar_zscore = Column(Float)
    month_extracted = Column(Integer)
    year = Column(Integer)
    dayofyear = Column(Integer)
    weekofyear = Column(Integer)
    __table_args__ = (UniqueConstraint('province_id', 'date', name='_forecast_province_date_uc'),)
    province = relationship("Province")
