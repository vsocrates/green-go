"""
Dummy ObservationBundle for local development and testing.

Scenario (2026-05-14, 09:30 UTC):
  - Tesla Model Y plugged in at 62% SoC, deadline Wed 07:00 (need 90%)
  - Tesla Wall Connector (paired to the Model Y)
  - Tesla Powerwall 3 at 78% SoC, currently SELF_RELIANCE
  - Enphase IQ Battery 5P at 45% SoC, currently SELF_RELIANCE
  - Two Enphase IQ8M inverters (observe-only) producing ~4.2 kW combined
  - Nest Learning Thermostat (3rd Gen) cooling at 23.5°C, target 22°C
  - Grid price $0.42/kWh (peak), off-peak $0.18 (21:00–07:00)
  - MER trough ~280 lbs/MWh at 02:00–05:00, peak ~510 lbs/MWh at 18:00
  - Sunny day, 27°C peak at 14:00; heavy cloud cover starts after 17:00
  - User slider = 0.2 (minimize_cost), EV deadline tomorrow 07:00
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.models import (
    BatteryState,
    CalendarEvent,
    ChargerState,
    DeviceStatus,
    DeviceUsage,
    DeviceUsage24h,
    EVReadyBy,
    HourlyUsage,
    HVACState,
    InverterState,
    MERForecast,
    MERPoint,
    MeterState,
    ObservationBundle,
    PricingInfo,
    SafetyFloor,
    ThermostatScheduleEntry,
    ToUEntry,
    UserPreferences,
    VehicleState,
    WeatherPoint,
)

UTC = timezone.utc

# Reference time: 2026-05-14 09:30 UTC
NOW = datetime(2026, 5, 14, 9, 30, 0, tzinfo=UTC)


def _dt(hour: int, minute: int = 0, day_offset: int = 0) -> datetime:
    base = NOW.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base + timedelta(days=day_offset)


# ---------------------------------------------------------------------------
# MER forecast — 72 one-hour buckets starting from NOW
# ---------------------------------------------------------------------------
# Pattern: morning peak → midday dip (solar) → late afternoon peak → overnight trough

_MER_PROFILE = [
    # hour 0–8 (09:30–17:30 local) — morning through late afternoon
    420, 430, 440, 460, 510, 500, 480, 460, 440,
    # hour 9–15 — afternoon slide down to evening peak
    420, 400, 380, 360, 370, 390,
    # hour 16–22 — late-night descent
    340, 310, 290, 280, 275, 278, 285,
    # hour 23–30 — overnight trough
    290, 300, 310, 320, 330, 340, 355, 365,
    # hour 31–47 — next day repeat (slightly higher, overcast)
    375, 390, 400, 410, 420, 415, 405, 395,
    380, 365, 350, 340, 330, 325, 330, 340,
    355, 365, 370, 375, 380, 385, 380, 370,
]


def _make_mer_forecast() -> MERForecast:
    points = []
    for i, mer in enumerate(_MER_PROFILE):
        ts = NOW + timedelta(hours=i)
        points.append(MERPoint(timestamp=ts, mer_lbs_per_mwh=float(mer)))
    return MERForecast(signal_type="co2_moer", region="CAISO_NORTH", points=points)


# ---------------------------------------------------------------------------
# Weather — 72 hourly buckets
# ---------------------------------------------------------------------------

def _make_weather() -> list[WeatherPoint]:
    weather = []
    for i in range(72):
        ts = NOW + timedelta(hours=i)
        day_hour = (ts.hour + i) % 24
        # Temp: peaks at 14:00, troughs at 05:00
        temp_c = 18.0 + 9.0 * max(0.0, 1.0 - abs(day_hour - 14) / 8.0)
        # Day 1: sunny until 17:00, then overcast
        if i < 8:
            cloud = 10.0
        elif i < 12:
            cloud = 5.0   # solar peak
        elif i < 19:
            cloud = 20.0
        else:
            cloud = 75.0  # overnight / day 2 overcast
        weather.append(
            WeatherPoint(
                timestamp=ts,
                temp_c=round(temp_c, 1),
                cloud_cover_pct=cloud,
                precip_mm=0.0,
            )
        )
    return weather


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def _make_pricing() -> PricingInfo:
    return PricingInfo(
        current_price_per_kwh=0.42,
        currency="USD",
        export_tariff_per_kwh=0.10,
        tou_schedule=[
            ToUEntry(
                label="peak",
                start_time="07:00",
                end_time="21:00",
                price_per_kwh=0.42,
                days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            ),
            ToUEntry(
                label="off_peak",
                start_time="21:00",
                end_time="07:00",
                price_per_kwh=0.18,
                days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Device status
# ---------------------------------------------------------------------------

def _make_device_status() -> DeviceStatus:
    return DeviceStatus(
        vehicles=[
            VehicleState(
                vendor="TESLA",
                model="Model Y",
                enode_vehicle_id="veh_xyz789",
                enode_user_id="user_abc123",
                soc_percent=62.0,
                range_km=220.0,
                is_plugged_in=True,
                is_charging=True,
                location_label="home_garage",
            )
        ],
        chargers=[
            ChargerState(
                vendor="TESLA",
                model="Wall Connector",
                enode_charger_id="chg_001",
                enode_user_id="user_abc123",
                enode_vehicle_id="veh_xyz789",
                is_charging=True,
                current_power_kw=7.2,
            )
        ],
        batteries=[
            BatteryState(
                vendor="TESLA",
                model="Powerwall 3",
                enode_battery_id="bat_001",
                enode_user_id="user_abc123",
                soc_percent=78.0,
                capacity_kwh=13.5,
                current_power_kw=0.0,
                current_operation_mode="SELF_RELIANCE",
                supported_modes=["SELF_RELIANCE", "TIME_OF_USE", "IMPORT_FOCUS", "EXPORT_FOCUS", "IDLE"],
            ),
            BatteryState(
                vendor="ENPHASE",
                model="IQ Battery 5P",
                enode_battery_id="bat_002",
                enode_user_id="user_abc123",
                soc_percent=45.0,
                capacity_kwh=5.0,
                current_power_kw=0.0,
                current_operation_mode="SELF_RELIANCE",
                supported_modes=["SELF_RELIANCE", "TIME_OF_USE", "IMPORT_FOCUS", "EXPORT_FOCUS"],
            ),
        ],
        hvacs=[
            HVACState(
                vendor="NEST",
                model="Nest Learning Thermostat (3rd Generation)",
                enode_hvac_id="hvac_001",
                enode_user_id="user_abc123",
                current_temp_c=23.5,
                target_temp_c=22.0,
                mode="COOL",
                is_active=True,
                has_active_hold=False,
            )
        ],
        inverters=[
            InverterState(
                vendor="ENPHASE",
                model="IQ8M Microinverter",
                enode_inverter_id="inv_001",
                enode_user_id="user_abc123",
                production_kw=2.1,
                status="normal",
            ),
            InverterState(
                vendor="ENPHASE",
                model="IQ8M Microinverter",
                enode_inverter_id="inv_002",
                enode_user_id="user_abc123",
                production_kw=2.1,
                status="normal",
            ),
        ],
        meters=[
            MeterState(
                vendor="ENPHASE",
                model="Enphase Integrated Consumption Meter",
                enode_meter_id="mtr_001",
                enode_user_id="user_abc123",
                consumption_kw=9.8,
                net_power_kw=5.6,  # net import after solar
            )
        ],
    )


# ---------------------------------------------------------------------------
# Device usage 24h
# ---------------------------------------------------------------------------

def _make_usage() -> DeviceUsage24h:
    def _flat_usage(device_id: str, device_type: str, alias: str, base_kw: float) -> DeviceUsage:
        hourly = []
        for h in range(24):
            ts = NOW - timedelta(hours=24 - h)
            hourly.append(HourlyUsage(timestamp=ts, power_kw=base_kw))
        return DeviceUsage(
            device_id=device_id, device_type=device_type, alias=alias, hourly_data=hourly
        )

    return DeviceUsage24h(
        entries=[
            _flat_usage("veh_xyz789", "vehicle", "tesla_model_y", 0.0),     # mostly idle
            _flat_usage("chg_001", "charger", "wall_connector", 7.2),        # charging overnight
            _flat_usage("bat_001", "battery", "powerwall_3", 0.5),
            _flat_usage("bat_002", "battery", "iq_battery_5p", 0.2),
            _flat_usage("hvac_001", "hvac", "nest_living_room", 1.8),
        ]
    )


# ---------------------------------------------------------------------------
# User preferences
# ---------------------------------------------------------------------------

def _make_preferences() -> UserPreferences:
    return UserPreferences(
        optimization_slider=0.2,  # minimize_cost
        ev_ready_by=[
            EVReadyBy(
                preference_id="pref_ev_ready_thu",
                enode_vehicle_id="veh_xyz789",
                target_soc_percent=90.0,
                deadline=_dt(7, 0, day_offset=1),  # tomorrow 07:00 UTC
            )
        ],
        device_unavailable_windows=[],
        thermostat_schedule=[
            ThermostatScheduleEntry(
                start_time="07:00",
                end_time="22:00",
                target_temp_c=22.0,
                mode="COOL",
            ),
            ThermostatScheduleEntry(
                start_time="22:00",
                end_time="07:00",
                target_temp_c=24.0,
                mode="COOL",
            ),
        ],
        safety_floors=[
            SafetyFloor(
                preference_id="pref_safety_ev_min_soc",
                device_id="veh_xyz789",
                min_ev_soc_percent=20.0,
            ),
            SafetyFloor(
                preference_id="pref_safety_bat_min_soc",
                device_id="bat_001",
                min_battery_soc_percent=10.0,
            ),
            SafetyFloor(
                preference_id="pref_safety_hvac",
                device_id="hvac_001",
                min_temp_c=18.0,
                max_temp_c=28.0,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def _make_calendar() -> list[CalendarEvent]:
    return [
        CalendarEvent(
            title="Work from home",
            start=_dt(9, 0),
            end=_dt(18, 0),
            implies_occupied=True,
            note="Home all day; comfort matters.",
        ),
        CalendarEvent(
            title="Evening out",
            start=_dt(19, 0),
            end=_dt(23, 0),
            implies_occupied=False,
            note="Good window for grid export or battery cycling.",
        ),
    ]


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def make_dummy_bundle() -> ObservationBundle:
    """Return a fully populated ObservationBundle for local testing."""
    return ObservationBundle(
        now=NOW,
        horizon_hours=72,
        preferences=_make_preferences(),
        calendar=_make_calendar(),
        device_status=_make_device_status(),
        device_usage_24h=_make_usage(),
        mer_forecast=_make_mer_forecast(),
        weather=_make_weather(),
        pricing=_make_pricing(),
    )
