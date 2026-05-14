"""
Entry point for running the energy management agent.

Usage:
    python -m agent.run               # live data where available, dummy for the rest
    python -m agent.run --dummy       # fully dummy data (no API calls)
    python -m agent.run --pretty      # human-readable summary output
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agent.agent import run_agent
from agent.dummy_data import make_dummy_bundle
from agent.models import (
    MERForecast,
    MERPoint,
    TemperatureState,
    ThermostatState,
)


def _merge_live_data(bundle):
    """Overlay live Enode and WattTime data onto a dummy bundle, in place.

    Device identification fields (vendor, model, enode IDs, supported_modes) stay
    from the dummy stubs. Charge-state and thermostat-state fields come from the
    live APIs when available.
    """

    # --- WattTime: MOER forecast ---
    try:
        from src.watt_time import get_moer_forecast
        live_moer = get_moer_forecast()
        bundle = bundle.model_copy(update={
            "mer_forecast": MERForecast(
                signal_type="co2_moer",
                region="CAISO_NORTH",
                points=[MERPoint(point_time=p.point_time, value=p.value) for p in live_moer],
            )
        })
        print(f"  MOER: {len(live_moer)} forecast points fetched", file=sys.stderr)
    except Exception as e:
        print(f"  MOER: fetch failed ({e}), using dummy", file=sys.stderr)

    # --- Enode: batteries, chargers, HVACs ---
    try:
        from src.enode import get_battery_charge_states, get_charger_charge_states, get_hvac_states

        live_batteries = get_battery_charge_states()
        live_chargers = get_charger_charge_states()
        live_hvacs = get_hvac_states()

        device_status = bundle.device_status

        updated_batteries = list(device_status.batteries)
        for i, lb in enumerate(live_batteries):
            if i < len(updated_batteries):
                updated_batteries[i] = updated_batteries[i].model_copy(update={
                    "status": lb.status,
                    "battery_capacity": lb.battery_capacity,
                    "battery_level": lb.battery_level,
                    "charge_rate": lb.charge_rate,
                    "discharge_limit": lb.discharge_limit,
                    "last_updated": lb.last_updated,
                })

        updated_chargers = list(device_status.chargers)
        for i, lc in enumerate(live_chargers):
            if i < len(updated_chargers):
                updated_chargers[i] = updated_chargers[i].model_copy(update={
                    "is_plugged_in": lc.is_plugged_in,
                    "is_charging": lc.is_charging,
                    "charge_rate": lc.charge_rate,
                    "max_current": lc.max_current,
                    "power_delivery_state": lc.power_delivery_state,
                    "plugged_in_vehicle_id": lc.plugged_in_vehicle_id,
                    "charge_rate_limit": lc.charge_rate_limit,
                    "last_updated": lc.last_updated,
                })

        updated_hvacs = list(device_status.hvacs)
        for i, lh in enumerate(live_hvacs):
            if i < len(updated_hvacs):
                ts = ThermostatState(
                    mode=lh.thermostat_state.mode,
                    heat_setpoint=lh.thermostat_state.heat_setpoint,
                    cool_setpoint=lh.thermostat_state.cool_setpoint,
                    hold_type=lh.thermostat_state.hold_type,
                    last_updated=lh.thermostat_state.last_updated,
                ) if lh.thermostat_state else None
                tmp = TemperatureState(
                    current_temperature=lh.temperature_state.current_temperature,
                    is_active=lh.temperature_state.is_active,
                    last_updated=lh.temperature_state.last_updated,
                ) if lh.temperature_state else None
                updated_hvacs[i] = updated_hvacs[i].model_copy(update={
                    "thermostat_state": ts,
                    "temperature_state": tmp,
                })

        bundle = bundle.model_copy(update={
            "device_status": device_status.model_copy(update={
                "batteries": updated_batteries,
                "chargers": updated_chargers,
                "hvacs": updated_hvacs,
            })
        })
        print(
            f"  Enode: {len(live_batteries)} batteries, {len(live_chargers)} chargers,"
            f" {len(live_hvacs)} HVACs fetched",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"  Enode: fetch failed ({e}), using dummy", file=sys.stderr)

    return bundle


async def main(pretty: bool = False, dummy: bool = False) -> None:
    print("Building ObservationBundle...", file=sys.stderr)
    bundle = make_dummy_bundle()

    if not dummy:
        print("Fetching live data...", file=sys.stderr)
        bundle = _merge_live_data(bundle)

    print(f"Invoking energy agent (now={bundle.now.isoformat()})...", file=sys.stderr)
    plan = await run_agent(bundle)

    if pretty:
        print(f"\nplan_id:   {plan.plan_id}")
        print(f"objective: {plan.objective}")
        print(f"generated: {plan.generated_at.isoformat()}")
        print(f"valid_until: {plan.valid_until.isoformat()}")
        print(f"total_actions: {plan.plan_summary.total_actions}")
        print(f"\nContext:")
        print(f"  grid_price:       ${plan.context.current_grid_price_per_kwh}/kWh")
        print(f"  solar_next_6h:    {plan.context.forecast_solar_kwh_next_6h} kWh")
        print(f"  load_next_6h:     {plan.context.forecast_load_kwh_next_6h} kWh")
        print(f"  home_occupied:    {plan.context.home_occupied}")

        for cls, actions in [
            ("vehicles", plan.actions.vehicles),
            ("chargers", plan.actions.chargers),
            ("batteries", plan.actions.batteries),
            ("hvacs", plan.actions.hvacs),
        ]:
            if actions:
                print(f"\n{cls.upper()}:")
                for alias, act in actions.items():
                    print(f"  [{alias}]")
                    print(f"    action:   {act.action}")
                    print(f"    schedule: {act.schedule.model_dump()}")
                    print(f"    reason:   {act.reason}")
                    print(f"    priority: {act.priority}")

        if plan.unmet_preferences:
            print("\nUNMET PREFERENCES:")
            for u in plan.unmet_preferences:
                print(f"  [{u.severity}] {u.preference_id}: {u.reason}")
        else:
            print("\nAll preferences satisfied.")
    else:
        print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run energy agent")
    parser.add_argument("--pretty", action="store_true", help="Human-readable output instead of JSON")
    parser.add_argument("--dummy", action="store_true", help="Use only dummy data (no API calls)")
    args = parser.parse_args()
    asyncio.run(main(pretty=args.pretty, dummy=args.dummy))
