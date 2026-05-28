"""
WattTime helper — fetches MOER real-time signal and hourly forecast
to populate the mer_forecast section of an ObservationBundle.

Uses the official `watttime` Python SDK (pip install watttime).
SDK docs: https://github.com/WattTime/watttime-python-client

Usage:
    import asyncio
    from helpers.watttime_client import WattTimeClient

    async def main():
        client = WattTimeClient.from_env()
        forecast = await client.get_mer_forecast(horizon_hours=72)
        realtime = await client.get_mer_realtime()

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

from dotenv import load_dotenv

from agent.models import MERForecast, MERPoint

load_dotenv()

UTC = timezone.utc


class WattTimeClient:
    """
    Thin async wrapper around the watttime SDK.

    The SDK is synchronous, so blocking calls are run in a thread pool
    via asyncio.to_thread to avoid blocking the event loop.
    """

    def __init__(
        self,
        username: str,
        password: str,
        region: str = "CAISO_NORTH",
    ) -> None:
        self._username = username
        self._password = password
        self._region = region

    @classmethod
    def from_env(cls) -> "WattTimeClient":
        return cls(
            username=os.environ["WATTTIME_USERNAME"],
            password=os.environ["WATTTIME_PASSWORD"],
            region=os.getenv("WATTTIME_REGION", "CAISO_NORTH"),
        )

    # ------------------------------------------------------------------
    # Real-time MOER
    # ------------------------------------------------------------------

    async def get_mer_realtime(self) -> MERPoint:
        """Return the current MOER value for the configured region."""
        point = await asyncio.to_thread(self._fetch_realtime_sync)
        return point

    def _fetch_realtime_sync(self) -> MERPoint:
        from watttime import WattTimeMyAccess  # type: ignore[import]

        client = WattTimeMyAccess(username=self._username, password=self._password)
        client.login()
        data = client.get_index(region=self._region, signal_type="co2_moer")
        # SDK returns a dict or DataFrame depending on version; normalise to MERPoint
        return self._parse_realtime(data)

    @staticmethod
    def _parse_realtime(data: Any) -> MERPoint:
        # watttime SDK may return a dict, list, or pandas DataFrame
        if hasattr(data, "iterrows"):
            # DataFrame
            row = next(data.iterrows())[1]
            ts = _to_utc_datetime(row.get("point_time") or row.get("timestamp"))
            value = float(row.get("value", 0.0))
        elif isinstance(data, list) and data:
            ts = _to_utc_datetime(data[0].get("point_time"))
            value = float(data[0].get("value", 0.0))
        elif isinstance(data, dict):
            ts = _to_utc_datetime(data.get("point_time") or data.get("timestamp"))
            value = float(data.get("value", 0.0))
        else:
            ts = datetime.now(UTC)
            value = 0.0
        return MERPoint(timestamp=ts, mer_lbs_per_mwh=value)

    # ------------------------------------------------------------------
    # Forecast MOER
    # ------------------------------------------------------------------

    async def get_mer_forecast(self, horizon_hours: int = 72) -> MERForecast:
        """Return an hourly MER forecast for the next horizon_hours."""
        forecast = await asyncio.to_thread(
            self._fetch_forecast_sync, horizon_hours
        )
        return forecast

    def _fetch_forecast_sync(self, horizon_hours: int) -> MERForecast:
        from watttime import WattTimeForecast  # type: ignore[import]

        client = WattTimeForecast(username=self._username, password=self._password)
        client.login()

        now = datetime.now(UTC)
        start = now.strftime("%Y-%m-%dT%H:%M+00:00")
        end = (now + timedelta(hours=horizon_hours)).strftime("%Y-%m-%dT%H:%M+00:00")

        data = client.get_forecast_pandas(
            region=self._region,
            signal_type="co2_moer",
            start=start,
            end=end,
        )
        return self._parse_forecast(data)

    def _parse_forecast(self, data: Any) -> MERForecast:
        points: list[MERPoint] = []

        if hasattr(data, "iterrows"):
            # pandas DataFrame
            for _, row in data.iterrows():
                ts = _to_utc_datetime(
                    row.get("point_time") or row.get("timestamp") or row.get("generated_at")
                )
                value = float(row.get("value", 0.0))
                points.append(MERPoint(timestamp=ts, mer_lbs_per_mwh=value))

        elif isinstance(data, list):
            for item in data:
                ts = _to_utc_datetime(item.get("point_time") or item.get("timestamp"))
                value = float(item.get("value", 0.0))
                points.append(MERPoint(timestamp=ts, mer_lbs_per_mwh=value))

        elif isinstance(data, dict):
            raw_points = data.get("data", [data])
            for item in raw_points:
                ts = _to_utc_datetime(item.get("point_time") or item.get("timestamp"))
                value = float(item.get("value", 0.0))
                points.append(MERPoint(timestamp=ts, mer_lbs_per_mwh=value))

        return MERForecast(
            signal_type="co2_moer",
            region=self._region,
            points=points,
        )

    # ------------------------------------------------------------------
    # Convenience: build full MERForecast (combines realtime + forecast)
    # ------------------------------------------------------------------

    async def build_mer_forecast(self, horizon_hours: int = 72) -> MERForecast:
        """
        Fetch the forecast (which already includes current + future points)
        and return as MERForecast.  Falls back gracefully if the API call fails.
        """
        try:
            return await self.get_mer_forecast(horizon_hours=horizon_hours)
        except Exception as exc:
            print(f"[WattTimeClient] Forecast fetch failed: {exc}. Returning empty forecast.")
            return MERForecast(
                signal_type="co2_moer",
                region=self._region,
                points=[],
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, str):
        # ISO 8601 with or without timezone
        s = value.replace("Z", "+00:00")
        return datetime.fromisoformat(s).astimezone(UTC)
    # Fallback
    return datetime.now(UTC)
