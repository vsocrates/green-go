from datetime import datetime
from pydantic import BaseModel


class MoerForecast(BaseModel):
    point_time: datetime
    value: float
