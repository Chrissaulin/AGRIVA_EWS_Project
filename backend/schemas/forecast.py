from pydantic import BaseModel


class RunForecastRequest(BaseModel):
    months_ahead: int = 6
