from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional

class RegionResponse(BaseModel):
    region_name: str
    cluster_wilayah: int
    risk_status: int = 0

    class Config:
        from_attributes = True

class MetricsSummary(BaseModel):
    region_name: Optional[str] = "Indonesia (All)"
    cluster_wilayah: Optional[int] = None
    avg_rainfall: float
    avg_spi_3m: float
    avg_temperature: float
    avg_wsi: float
    avg_soil_moisture: float
    avg_fpar: float
    total_alerts: int

class TrendRecord(BaseModel):
    date: date
    rainfall: float
    spi_3m: float
    temperature: float
    wsi: float
    soil_moisture: float
    fpar: float
    target_ews: int

    class Config:
        from_attributes = True

class SimulationInput(BaseModel):
    region_name: str = Field(..., example="Jawa Timur")
    rainfall: float = Field(..., description="Rainfall in mm", example=50.0)
    spi_3m: float = Field(..., description="Standardized Precipitation Index", example=0.0)
    temperature: float = Field(..., description="Temperature in °C", example=26.0)
    wsi: float = Field(..., description="Water Satisfaction Index (WSI)", example=90.0)
    solar_radiation: float = Field(..., description="Solar Radiation", example=200000.0)
    soil_moisture: float = Field(..., description="Soil Moisture level", example=0.3)
    fpar: float = Field(..., description="FPAR index", example=60.0)
    fpar_zscore: float = Field(..., description="FPAR Z-Score", example=0.0)
    month: int = Field(..., description="Month of year (1-12)", example=5)

class SimulationResponse(BaseModel):
    region_name: str
    cluster_wilayah: int
    probability: float = Field(..., description="Warning probability (0.0 to 1.0)")
    threshold_used: float = Field(..., description="Decision threshold applied")
    is_warning: bool = Field(..., description="True if probability >= threshold (Bahaya)")
    status_label: str = Field(..., description="Aman (Safe) or Bahaya (Warning)")

class ForecastRequest(BaseModel):
    region_name: str = Field(..., example="Jawa Timur")
    steps: int = Field(5, ge=1, le=12, description="Number of future dekads (steps) to forecast")

class ForecastResponseRecord(BaseModel):
    step: int
    date: date
    rainfall: float
    spi_3m: float
    temperature: float
    wsi: float
    solar_radiation: float
    soil_moisture: float
    fpar: float
    fpar_zscore: float

class ForecastResponse(BaseModel):
    region_name: str
    forecasts: List[ForecastResponseRecord]
