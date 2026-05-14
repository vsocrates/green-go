import os
from datetime import datetime
from typing import Literal

from pydantic import TypeAdapter
from dotenv import load_dotenv

from watttime import WattTimeForecast
from src.types.moer_forecast import MoerForecast

load_dotenv()


WT_USERNAME = os.getenv('WATTTIME_USERNAME')
WT_PASSWORD = os.getenv('WATTTIME_PASSWORD')


def get_moer_forecast(region: Literal['CAISO_NORTH'] = 'CAISO_NORTH'):

    wt_forecast = WattTimeForecast(WT_USERNAME, WT_PASSWORD)

    response = wt_forecast.get_forecast_json(region=region,
                                             signal_type='co2_moer')

    return TypeAdapter(list[MoerForecast]).validate_python(response['data'])


if __name__ == '__main__':
    print(get_moer_forecast())
