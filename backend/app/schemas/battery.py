from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BatteryChargeState(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    status: str | None
    battery_capacity: float | None
    battery_level: float | None
    charge_rate: float | None
    discharge_limit: float | None
    last_updated: datetime | None
