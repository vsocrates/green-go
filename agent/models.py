"""
Pydantic models for the Home Energy Management Agent.

ObservationBundle  — structured input assembled by external code (Enode + WattTime + Calendar + Prefs).
ActionPlan         — structured output emitted by the agent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums / literals
# ---------------------------------------------------------------------------

VehicleVerb = Literal["START_CHARGING", "STOP_CHARGING"]
ChargerVerb = Literal["START_CHARGING", "STOP_CHARGING"]
BatteryVerb = Literal["SET_OPERATION_MODE"]
HVACVerb = Literal["SET_PERMANENT_HOLD", "RETURN_TO_SCHEDULE"]
BatteryMode = Literal["SELF_RELIANCE", "TIME_OF_USE", "IMPORT_FOCUS", "EXPORT_FOCUS", "IDLE"]
HVACMode = Literal["HEAT", "COOL", "HEATCOOL"]
Objective = Literal["minimize_cost", "balanced", "respect_preferences"]
Severity = Literal["minor", "moderate", "major"]
Priority = Literal[1, 2, 3]


# ---------------------------------------------------------------------------
# Schedule types (discriminated union on `type`)
# ---------------------------------------------------------------------------

class ImmediateSchedule(BaseModel):
    type: Literal["immediate"]


class DeferredSchedule(BaseModel):
    """Flexible start; the executor must complete by end_by."""
    type: Literal["deferred"]
    start_at: datetime
    end_by: datetime


class WindowSchedule(BaseModel):
    """Fixed window — active between start_at and end_at."""
    type: Literal["window"]
    start_at: datetime
    end_at: datetime


class ContinuousSchedule(BaseModel):
    """Ongoing, no defined end."""
    type: Literal["continuous"]


Schedule = Annotated[
    Union[ImmediateSchedule, DeferredSchedule, WindowSchedule, ContinuousSchedule],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Fallback action (generic mini-action; class context determines allowed verbs)
# ---------------------------------------------------------------------------

class FallbackAction(BaseModel):
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-class device actions
# ---------------------------------------------------------------------------

class VehicleAction(BaseModel):
    vendor: Literal["TESLA"]
    model: str
    enode_vehicle_id: str
    enode_user_id: str
    action: VehicleVerb
    parameters: dict[str, Any] = Field(default_factory=dict)
    schedule: Schedule
    reason: str = Field(description="1-2 factual sentences referencing the specific observation that drove this choice.")
    priority: Priority
    fallback_action: FallbackAction | None = None
    constraints: dict[str, Any] | None = None


class ChargerAction(BaseModel):
    vendor: Literal["TESLA"]
    model: str
    enode_charger_id: str
    enode_user_id: str
    enode_vehicle_id: str | None = None
    action: ChargerVerb
    parameters: dict[str, Any] = Field(default_factory=dict)
    schedule: Schedule
    reason: str
    priority: Priority
    fallback_action: FallbackAction | None = None
    constraints: dict[str, Any] | None = None


class BatteryAction(BaseModel):
    vendor: Literal["TESLA", "ENPHASE"]
    model: str
    enode_battery_id: str
    enode_user_id: str
    action: BatteryVerb
    parameters: dict[str, Any] = Field(
        description='For SET_OPERATION_MODE: {"mode": "<BatteryMode>"}. Mode must be in device supported_modes.',
    )
    schedule: Schedule
    reason: str
    priority: Priority
    fallback_action: FallbackAction | None = None
    constraints: dict[str, Any] | None = None


class HVACAction(BaseModel):
    vendor: Literal["NEST"]
    model: str
    enode_hvac_id: str
    enode_user_id: str
    action: HVACVerb
    parameters: dict[str, Any] = Field(
        description=(
            'For SET_PERMANENT_HOLD: {"target_temp_c": <float>, "mode": "<HVACMode>"}. '
            'For RETURN_TO_SCHEDULE: {}.'
        ),
    )
    schedule: Schedule
    reason: str
    priority: Priority
    fallback_action: FallbackAction | None = None
    constraints: dict[str, Any] | None = None


class PlanActions(BaseModel):
    vehicles: dict[str, VehicleAction] = Field(default_factory=dict)
    chargers: dict[str, ChargerAction] = Field(default_factory=dict)
    batteries: dict[str, BatteryAction] = Field(default_factory=dict)
    hvacs: dict[str, HVACAction] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# ActionPlan top-level
# ---------------------------------------------------------------------------

class PlanContext(BaseModel):
    current_grid_price_per_kwh: float | None = None
    forecast_solar_kwh_next_6h: float
    forecast_load_kwh_next_6h: float
    home_occupied: bool


class UnmetPreference(BaseModel):
    preference_id: str
    reason: str
    severity: Severity


class PlanSummary(BaseModel):
    total_actions: int


class ActionPlan(BaseModel):
    plan_id: str = Field(description='Format: "plan_<ISO_UTC>_<seq>" e.g. plan_2026-05-14T09:30:00Z_001')
    generated_at: datetime
    valid_until: datetime = Field(description="generated_at + 1 hour")
    planning_horizon_hours: int = 24
    objective: Objective
    context: PlanContext
    actions: PlanActions
    unmet_preferences: list[UnmetPreference] = Field(default_factory=list)
    plan_summary: PlanSummary


# ===========================================================================
# ObservationBundle — input to the agent
# ===========================================================================

# ---------------------------------------------------------------------------
# User preferences
# ---------------------------------------------------------------------------

class EVReadyBy(BaseModel):
    preference_id: str
    enode_vehicle_id: str
    target_soc_percent: float
    deadline: datetime


class DeviceUnavailableWindow(BaseModel):
    preference_id: str
    enode_device_id: str
    device_type: Literal["vehicle", "charger", "battery", "hvac"]
    start: datetime
    end: datetime
    reason: str | None = None


class ThermostatScheduleEntry(BaseModel):
    start_time: str = Field(description="HH:MM local time")
    end_time: str = Field(description="HH:MM local time")
    target_temp_c: float
    mode: HVACMode


class SafetyFloor(BaseModel):
    preference_id: str
    device_id: str
    min_ev_soc_percent: float | None = None
    min_battery_soc_percent: float | None = None
    min_temp_c: float | None = None
    max_temp_c: float | None = None


class UserPreferences(BaseModel):
    optimization_slider: float = Field(ge=0.0, le=1.0)
    ev_ready_by: list[EVReadyBy] = Field(default_factory=list)
    device_unavailable_windows: list[DeviceUnavailableWindow] = Field(default_factory=list)
    thermostat_schedule: list[ThermostatScheduleEntry] = Field(default_factory=list)
    safety_floors: list[SafetyFloor] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

class CalendarEvent(BaseModel):
    title: str
    start: datetime
    end: datetime
    implies_occupied: bool = True
    note: str | None = None


# ---------------------------------------------------------------------------
# Device status models
# ---------------------------------------------------------------------------

class VehicleState(BaseModel):
    vendor: Literal["TESLA"]
    model: str
    enode_vehicle_id: str
    enode_user_id: str
    soc_percent: float
    range_km: float | None = None
    is_plugged_in: bool
    is_charging: bool
    location_label: str | None = None


class ChargerState(BaseModel):
    vendor: Literal["TESLA"]
    model: str
    enode_charger_id: str
    enode_user_id: str
    enode_vehicle_id: str | None = None
    is_charging: bool
    current_power_kw: float | None = None


class BatteryState(BaseModel):
    vendor: Literal["TESLA", "ENPHASE"]
    model: str
    enode_battery_id: str
    enode_user_id: str
    soc_percent: float
    capacity_kwh: float
    current_power_kw: float | None = None
    current_operation_mode: BatteryMode | None = None
    supported_modes: list[BatteryMode] = Field(
        description="Exact list of modes supported by this device. Agent must not emit a mode outside this list.",
    )


class HVACState(BaseModel):
    vendor: Literal["NEST"]
    model: str
    enode_hvac_id: str
    enode_user_id: str
    current_temp_c: float
    target_temp_c: float | None = None
    mode: Literal["HEAT", "COOL", "HEATCOOL", "OFF", "MANUAL_ECO"]
    is_active: bool
    has_active_hold: bool = False


class InverterState(BaseModel):
    """Observe-only. No commands emitted for inverters."""
    vendor: Literal["TESLA", "ENPHASE"]
    model: str
    enode_inverter_id: str
    enode_user_id: str
    production_kw: float | None = None
    status: str | None = None


class MeterState(BaseModel):
    """Observe-only. No commands emitted for meters."""
    vendor: Literal["TESLA", "ENPHASE"]
    model: str
    enode_meter_id: str
    enode_user_id: str
    consumption_kw: float | None = None
    net_power_kw: float | None = None


class DeviceStatus(BaseModel):
    vehicles: list[VehicleState] = Field(default_factory=list)
    chargers: list[ChargerState] = Field(default_factory=list)
    batteries: list[BatteryState] = Field(default_factory=list)
    hvacs: list[HVACState] = Field(default_factory=list)
    inverters: list[InverterState] = Field(default_factory=list)
    meters: list[MeterState] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Device usage (last 24h)
# ---------------------------------------------------------------------------

class HourlyUsage(BaseModel):
    timestamp: datetime
    power_kw: float


class DeviceUsage(BaseModel):
    device_id: str
    device_type: Literal["vehicle", "charger", "battery", "hvac", "inverter", "meter"]
    alias: str | None = None
    hourly_data: list[HourlyUsage]


class DeviceUsage24h(BaseModel):
    entries: list[DeviceUsage] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# MER forecast (WattTime)
# ---------------------------------------------------------------------------

class MERPoint(BaseModel):
    timestamp: datetime
    mer_lbs_per_mwh: float


class MERForecast(BaseModel):
    signal_type: str = "co2_moer"
    region: str
    points: list[MERPoint]


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

class WeatherPoint(BaseModel):
    timestamp: datetime
    temp_c: float
    cloud_cover_pct: float = Field(ge=0.0, le=100.0)
    precip_mm: float = 0.0


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

class ToUEntry(BaseModel):
    label: str = Field(description='e.g. "peak" or "off_peak"')
    start_time: str = Field(description="HH:MM local")
    end_time: str = Field(description="HH:MM local")
    price_per_kwh: float
    days: list[str] = Field(description='e.g. ["Mon","Tue","Wed","Thu","Fri"]')


class PricingInfo(BaseModel):
    current_price_per_kwh: float
    currency: str = "USD"
    tou_schedule: list[ToUEntry] | None = None
    export_tariff_per_kwh: float | None = None


# ---------------------------------------------------------------------------
# ObservationBundle (top-level input)
# ---------------------------------------------------------------------------

class ObservationBundle(BaseModel):
    now: datetime
    horizon_hours: int = 72
    preferences: UserPreferences
    calendar: list[CalendarEvent] = Field(default_factory=list)
    device_status: DeviceStatus
    device_usage_24h: DeviceUsage24h
    mer_forecast: MERForecast
    weather: list[WeatherPoint]
    pricing: PricingInfo | None = None
