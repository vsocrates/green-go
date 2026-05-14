from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ThermostatState(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mode: str | None
    heat_setpoint: float | None
    cool_setpoint: float | None
    hold_type: str | None
    last_updated: datetime | None


class TemperatureState(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    current_temperature: float | None
    is_active: bool | None
    last_updated: datetime | None


class HVACState(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    thermostat_state: ThermostatState | None
    temperature_state: TemperatureState | None
