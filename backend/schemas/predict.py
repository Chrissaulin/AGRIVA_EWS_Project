from pydantic import BaseModel


class PredictionRequest(BaseModel):
    province: str
    Rainfall: float
    SPI_3_months: float
    Temperature: float
    WSI: float
    Solar_Radiation: float
    Soil_Moisture: float
    FPAR: float
    FPAR_zscore: float
    month_extracted: int


class PredictionResponse(BaseModel):
    province: str
    cluster: int
    prediction: int
    status: str
    probability: dict
    threshold: float
