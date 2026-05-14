import os

import httpx
from pydantic import TypeAdapter
from dotenv import load_dotenv

try:
    from src.datatypes.battery import BatteryChargeState
    from src.datatypes.charger import ChargerChargeState
    from src.datatypes.hvac import HVACState
except ImportError:
    from datatypes.battery import BatteryChargeState
    from datatypes.charger import ChargerChargeState
    from datatypes.hvac import HVACState

load_dotenv()

ENODE_BASE_URL = "https://enode-api.sandbox.enode.io"
ENODE_CLIENT_ID = os.getenv("ENODE_CLIENT_ID")
ENODE_CLIENT_SECRET = os.getenv("ENODE_CLIENT_SECRET")


def _get_access_token() -> str:
    response = httpx.post(
        "https://oauth.sandbox.enode.io/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=(ENODE_CLIENT_ID, ENODE_CLIENT_SECRET),
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_battery_charge_states() -> list[BatteryChargeState]:
    token = _get_access_token()
    response = httpx.get(
        f"{ENODE_BASE_URL}/batteries",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return TypeAdapter(list[BatteryChargeState]).validate_python(
        [b["chargeState"] for b in response.json()["data"]]
    )


def get_charger_charge_states() -> list[ChargerChargeState]:
    token = _get_access_token()
    response = httpx.get(
        f"{ENODE_BASE_URL}/chargers",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return TypeAdapter(list[ChargerChargeState]).validate_python(
        [c["chargeState"] for c in response.json()["data"]]
    )


def get_hvac_states() -> list[HVACState]:
    token = _get_access_token()
    response = httpx.get(
        f"{ENODE_BASE_URL}/hvacs",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return TypeAdapter(list[HVACState]).validate_python(
        [{"thermostatState": h["thermostatState"], "temperatureState": h["temperatureState"]} for h in response.json()["data"]]
    )


if __name__ == "__main__":
    print(get_battery_charge_states())
    print(get_charger_charge_states())
    print(get_hvac_states())
