import os

import httpx
from pydantic import TypeAdapter
from dotenv import load_dotenv

from datatypes.battery import BatteryChargeState

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


if __name__ == "__main__":
    print(get_battery_charge_states())
