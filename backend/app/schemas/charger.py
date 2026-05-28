from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ChargerChargeState(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    is_plugged_in: bool | None
    is_charging: bool | None
    charge_rate: float | None
    last_updated: datetime | None
    max_current: float | None
    power_delivery_state: str | None
    plugged_in_vehicle_id: str | None
    charge_rate_limit: float | None
