from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ProvinceInfo(BaseModel):
    name: str
    cluster: int
