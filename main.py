"""
main.py — Home Energy Management Agent entry point.

Flow:
  1. Build an empty ObservationBundle (now + defaults)
  2. Call each fetch_* function to populate one section of the bundle
     (fill in the # TODO bodies with real API calls)
  3. Run the Pydantic AI agent
  4. Print the ActionPlan as JSON

Environment variables (see .env.example):
  ANTHROPIC_API_KEY, ENODE_CLIENT_ID, ENODE_CLIENT_SECRET, ENODE_USER_ID,
  WATTTIME_USERNAME, WATTTIME_PASSWORD, WATTTIME_REGION
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from agent.agent import run_agent
from agent.models import (
    DeviceStatus,
    DeviceUsage24h,
    MERForecast,
    ObservationBundle,
    UserPreferences,
)
from helpers.enode_client import EnodeClient
from helpers.watttime_client import WattTimeClient

load_dotenv()

UTC = timezone.utc


# ---------------------------------------------------------------------------
# 1. Bundle scaffold
# ---------------------------------------------------------------------------

def build_initial_bundle() -> ObservationBundle:
    """Return a bundle with `now` set and all other sections at empty defaults."""
    return ObservationBundle(
        now=datetime.now(UTC),
        preferences=UserPreferences(optimization_slider=0.5),
        device_status=DeviceStatus(),
        device_usage_24h=DeviceUsage24h(),
        mer_forecast=MERForecast(
            region=os.getenv("WATTTIME_REGION", "CAISO_NORTH"),
            points=[],
        ),
        weather=[],
    )


# ---------------------------------------------------------------------------
# 2. Section fetchers — implement each with real API calls
# ---------------------------------------------------------------------------

async def fetch_preferences(bundle: ObservationBundle) -> ObservationBundle:
    """
    Populate bundle.preferences from your preferences store / config.

    Fields to set:
      bundle.preferences.optimization_slider          float [0.0, 1.0]
      bundle.preferences.ev_ready_by                  list[EVReadyBy]
      bundle.preferences.device_unavailable_windows   list[DeviceUnavailableWindow]
      bundle.preferences.thermostat_schedule          list[ThermostatScheduleEntry]
      bundle.preferences.safety_floors                list[SafetyFloor]
    """
    # TODO: implement
    return bundle


async def fetch_calendar(bundle: ObservationBundle) -> ObservationBundle:
    """
    Populate bundle.calendar from Google Calendar API.

    Fields to set:
      bundle.calendar   list[CalendarEvent]
    """
    # TODO: implement
    return bundle


async def fetch_device_status(
    bundle: ObservationBundle,
    enode: EnodeClient,
    user_id: str,
) -> ObservationBundle:
    """
    Populate bundle.device_status from Enode.

    Fields to set:
      bundle.device_status   DeviceStatus (vehicles, chargers, batteries,
                             hvacs, inverters, meters)

    Example:
      bundle.device_status = await enode.build_device_status(user_id)
    """
    # TODO: implement
    return bundle


async def fetch_device_usage_24h(
    bundle: ObservationBundle,
    enode: EnodeClient,
    user_id: str,
) -> ObservationBundle:
    """
    Populate bundle.device_usage_24h from Enode energy stats.

    Fields to set:
      bundle.device_usage_24h   DeviceUsage24h (hourly kW per device, last 24 h)

    Example:
      bundle.device_usage_24h = await enode.build_device_usage_24h(user_id)
    """
    # TODO: implement
    return bundle


async def fetch_mer_forecast(
    bundle: ObservationBundle,
    watttime: WattTimeClient,
) -> ObservationBundle:
    """
    Populate bundle.mer_forecast from WattTime.

    Fields to set:
      bundle.mer_forecast   MERForecast (hourly MOER lbs/MWh for horizon_hours)

    Example:
      bundle.mer_forecast = await watttime.build_mer_forecast(
          horizon_hours=bundle.horizon_hours
      )
    """
    # TODO: implement
    return bundle


async def fetch_weather(bundle: ObservationBundle) -> ObservationBundle:
    """
    Populate bundle.weather from OpenWeatherMap or similar.

    Fields to set:
      bundle.weather   list[WeatherPoint]
                       one entry per hour covering at least horizon_hours
                       fields: timestamp (UTC), temp_c, cloud_cover_pct, precip_mm
    """
    # TODO: implement
    return bundle


async def fetch_pricing(bundle: ObservationBundle) -> ObservationBundle:
    """
    Populate bundle.pricing from your utility's API or a static config.

    Fields to set:
      bundle.pricing   PricingInfo
                       fields: current_price_per_kwh, currency,
                               tou_schedule (list[ToUEntry] or None),
                               export_tariff_per_kwh (or None)
    """
    # TODO: implement
    return bundle


# ---------------------------------------------------------------------------
# 3. Orchestration
# ---------------------------------------------------------------------------

async def main() -> None:
    enode = EnodeClient.from_env()
    watttime = WattTimeClient.from_env()
    user_id = os.environ["ENODE_USER_ID"]

    bundle = build_initial_bundle()

    # Preferences and calendar first — device fetch may reference them
    bundle = await fetch_preferences(bundle)
    bundle = await fetch_calendar(bundle)

    # Remaining sections are independent — fetch in parallel
    # Each function mutates its own field on the shared bundle object
    await asyncio.gather(
        fetch_device_status(bundle, enode, user_id),
        fetch_device_usage_24h(bundle, enode, user_id),
        fetch_mer_forecast(bundle, watttime),
        fetch_weather(bundle),
        fetch_pricing(bundle),
    )

    plan = await run_agent(bundle)
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
