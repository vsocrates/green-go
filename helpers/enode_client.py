"""
Enode API helper — fetches all device data needed to populate DeviceStatus
and DeviceUsage24h sections of an ObservationBundle.

Authentication: OAuth 2.0 client credentials (POST /oauth2/token).
Token is cached in-memory until 60 s before expiry.

Usage:
    import asyncio
    from helpers.enode_client import EnodeClient

    async def main():
        client = EnodeClient.from_env()
        device_status = await client.build_device_status(user_id="<enode_user_id>")
        usage_24h = await client.build_device_usage_24h(user_id="<enode_user_id>")

    asyncio.run(main())
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from dotenv import load_dotenv

from agent.models import (
    BatteryMode,
    BatteryState,
    ChargerState,
    DeviceStatus,
    DeviceUsage,
    DeviceUsage24h,
    HourlyUsage,
    HVACState,
    InverterState,
    MeterState,
    VehicleState,
)

load_dotenv()

UTC = timezone.utc


class EnodeClient:
    """Async Enode API client.  One instance per process; reuse across calls."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = "https://enode-api.production.enode.io",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._token: str | None = None
        self._token_expiry: float = 0.0

    @classmethod
    def from_env(cls) -> "EnodeClient":
        return cls(
            client_id=os.environ["ENODE_CLIENT_ID"],
            client_secret=os.environ["ENODE_CLIENT_SECRET"],
            base_url=os.getenv("ENODE_BASE_URL", "https://enode-api.production.enode.io"),
        )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expiry:
            return self._token

        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{self._base_url}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()

        self._token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expiry = time.monotonic() + expires_in - 60
        return self._token

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._get_token()
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Raw list endpoints
    # ------------------------------------------------------------------

    async def list_vehicles(self, user_id: str) -> list[dict]:
        data = await self._get(f"/users/{user_id}/vehicles")
        return data.get("data", data) if isinstance(data, dict) else data

    async def list_chargers(self, user_id: str) -> list[dict]:
        data = await self._get(f"/users/{user_id}/chargers")
        return data.get("data", data) if isinstance(data, dict) else data

    async def list_batteries(self, user_id: str) -> list[dict]:
        data = await self._get(f"/users/{user_id}/batteries")
        return data.get("data", data) if isinstance(data, dict) else data

    async def list_hvacs(self, user_id: str) -> list[dict]:
        data = await self._get(f"/users/{user_id}/hvacs")
        return data.get("data", data) if isinstance(data, dict) else data

    async def list_inverters(self, user_id: str) -> list[dict]:
        data = await self._get(f"/users/{user_id}/inverters")
        return data.get("data", data) if isinstance(data, dict) else data

    async def list_meters(self, user_id: str) -> list[dict]:
        data = await self._get(f"/users/{user_id}/meters")
        return data.get("data", data) if isinstance(data, dict) else data

    # ------------------------------------------------------------------
    # Parsed device-state models
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_vehicle(raw: dict) -> VehicleState:
        charge = raw.get("chargeState", {}) or {}
        return VehicleState(
            vendor="TESLA",
            model=raw.get("model", "Unknown"),
            enode_vehicle_id=raw["id"],
            enode_user_id=raw.get("userId", ""),
            soc_percent=charge.get("batteryLevel", 0.0),
            range_km=charge.get("range", None),
            is_plugged_in=charge.get("isPluggedIn", False),
            is_charging=charge.get("isCharging", False),
            location_label=raw.get("locationId") or raw.get("location", {}).get("id"),
        )

    @staticmethod
    def _parse_charger(raw: dict) -> ChargerState:
        charge = raw.get("chargeState", {}) or {}
        return ChargerState(
            vendor="TESLA",
            model=raw.get("model", "Wall Connector"),
            enode_charger_id=raw["id"],
            enode_user_id=raw.get("userId", ""),
            enode_vehicle_id=raw.get("linkedVehicleId") or raw.get("vehicleId"),
            is_charging=charge.get("isCharging", False),
            current_power_kw=charge.get("powerDeliveryState", {}).get("powerInWatts", 0) / 1000
            if charge.get("powerDeliveryState")
            else None,
        )

    @staticmethod
    def _parse_battery(raw: dict) -> BatteryState:
        info = raw.get("information", {}) or {}
        state = raw.get("chargeState", {}) or {}
        capabilities = raw.get("capabilities", {}) or {}

        vendor_str = (info.get("brand") or raw.get("vendor", "TESLA")).upper()
        vendor = "ENPHASE" if "ENPHASE" in vendor_str else "TESLA"

        # Build supported modes from capabilities
        _all_modes: list[BatteryMode] = [
            "SELF_RELIANCE", "TIME_OF_USE", "IMPORT_FOCUS", "EXPORT_FOCUS", "IDLE"
        ]
        supported: list[BatteryMode] = []
        cap_modes = capabilities.get("setOperationMode", {}).get("supportedModes", [])
        if cap_modes:
            for m in cap_modes:
                if m in _all_modes:
                    supported.append(m)
        else:
            # Reasonable defaults when capabilities are not returned
            supported = (
                ["SELF_RELIANCE", "TIME_OF_USE", "IMPORT_FOCUS", "EXPORT_FOCUS", "IDLE"]
                if vendor == "TESLA"
                else ["SELF_RELIANCE", "TIME_OF_USE", "IMPORT_FOCUS", "EXPORT_FOCUS"]
            )

        return BatteryState(
            vendor=vendor,
            model=info.get("model") or raw.get("model", "Unknown"),
            enode_battery_id=raw["id"],
            enode_user_id=raw.get("userId", ""),
            soc_percent=state.get("batteryLevel", 0.0),
            capacity_kwh=info.get("capacity", 0.0),
            current_power_kw=state.get("power", None),
            current_operation_mode=state.get("operationMode"),
            supported_modes=supported,
        )

    @staticmethod
    def _parse_hvac(raw: dict) -> HVACState:
        info = raw.get("information", {}) or {}
        state = raw.get("thermostatState", {}) or {}
        return HVACState(
            vendor="NEST",
            model=info.get("model") or raw.get("model", "Nest Thermostat"),
            enode_hvac_id=raw["id"],
            enode_user_id=raw.get("userId", ""),
            current_temp_c=state.get("ambientTemperature", 20.0),
            target_temp_c=state.get("heatSetpoint") or state.get("coolSetpoint"),
            mode=state.get("mode", "OFF").upper(),
            is_active=state.get("hvacMode") not in (None, "OFF", "MANUAL_ECO"),
            has_active_hold=state.get("hold", False),
        )

    @staticmethod
    def _parse_inverter(raw: dict) -> InverterState:
        info = raw.get("information", {}) or {}
        state = raw.get("productionState", {}) or {}
        vendor_str = (info.get("brand") or "ENPHASE").upper()
        vendor = "TESLA" if "TESLA" in vendor_str else "ENPHASE"
        return InverterState(
            vendor=vendor,
            model=info.get("model") or raw.get("model", "Unknown"),
            enode_inverter_id=raw["id"],
            enode_user_id=raw.get("userId", ""),
            production_kw=state.get("productionRate", None),
            status=state.get("status"),
        )

    @staticmethod
    def _parse_meter(raw: dict) -> MeterState:
        info = raw.get("information", {}) or {}
        state = raw.get("consumptionState", {}) or {}
        vendor_str = (info.get("brand") or "ENPHASE").upper()
        vendor = "TESLA" if "TESLA" in vendor_str else "ENPHASE"
        return MeterState(
            vendor=vendor,
            model=info.get("model") or raw.get("model", "Unknown"),
            enode_meter_id=raw["id"],
            enode_user_id=raw.get("userId", ""),
            consumption_kw=state.get("consumptionRate", None),
            net_power_kw=state.get("netPower", None),
        )

    # ------------------------------------------------------------------
    # High-level builders
    # ------------------------------------------------------------------

    async def build_device_status(self, user_id: str) -> DeviceStatus:
        """Fetch all device types in parallel and return a populated DeviceStatus."""
        import asyncio

        results = await asyncio.gather(
            self.list_vehicles(user_id),
            self.list_chargers(user_id),
            self.list_batteries(user_id),
            self.list_hvacs(user_id),
            self.list_inverters(user_id),
            self.list_meters(user_id),
            return_exceptions=True,
        )

        def _safe(raw_list, parser):
            if isinstance(raw_list, Exception):
                print(f"[EnodeClient] Warning: fetch failed — {raw_list}")
                return []
            return [parser(r) for r in raw_list]

        return DeviceStatus(
            vehicles=_safe(results[0], self._parse_vehicle),
            chargers=_safe(results[1], self._parse_charger),
            batteries=_safe(results[2], self._parse_battery),
            hvacs=_safe(results[3], self._parse_hvac),
            inverters=_safe(results[4], self._parse_inverter),
            meters=_safe(results[5], self._parse_meter),
        )

    async def build_device_usage_24h(self, user_id: str) -> DeviceUsage24h:
        """
        Fetch 24h energy usage for all devices.

        Enode exposes energy statistics via /users/{userId}/devices/{deviceId}/energy
        or per-class endpoints. We aggregate across all device types here.

        NOTE: Enode's energy history API may not be available for all device classes
        or account tiers. The entries list will be empty for unsupported devices.
        """
        device_status = await self.build_device_status(user_id)
        entries: list[DeviceUsage] = []

        # Chargers have energy statistics
        for charger in device_status.chargers:
            hourly = await self._fetch_charger_energy(user_id, charger.enode_charger_id)
            if hourly:
                entries.append(
                    DeviceUsage(
                        device_id=charger.enode_charger_id,
                        device_type="charger",
                        alias=f"{charger.model.lower().replace(' ', '_')}_{charger.enode_charger_id[-4:]}",
                        hourly_data=hourly,
                    )
                )

        return DeviceUsage24h(entries=entries)

    async def _fetch_charger_energy(
        self, user_id: str, charger_id: str
    ) -> list[HourlyUsage]:
        """Fetch hourly energy draw for a charger from Enode's energy stats endpoint."""
        try:
            from datetime import timedelta

            now = datetime.now(UTC)
            start = (now - timedelta(hours=24)).isoformat()
            end = now.isoformat()
            data = await self._get(
                f"/users/{user_id}/chargers/{charger_id}/energy",
                params={"startDate": start, "endDate": end, "resolution": "HOUR"},
            )
            buckets = data.get("data", [])
            result = []
            for bucket in buckets:
                ts = datetime.fromisoformat(bucket["startDate"].replace("Z", "+00:00"))
                kw = bucket.get("consumedKwh", 0.0)
                result.append(HourlyUsage(timestamp=ts, power_kw=kw))
            return result
        except Exception as exc:
            print(f"[EnodeClient] Could not fetch energy for charger {charger_id}: {exc}")
            return []
