"""
Forecast Service
================
NASA POWER (weather_service.py) is historical/near-real-time only — it lags
~2-3 days behind today, so it CANNOT tell us "will it rain tomorrow?".

For that, we use Open-Meteo (https://open-meteo.com) — also free, no API key,
and gives up to 16-day forward forecasts. This powers:
  - Pest risk forecasting 3-5 days ahead
  - Irrigation advisory's "skip if rain expected in next 2 days" logic

If you later get an OpenWeatherMap key, you can swap this module out without
touching any downstream code, since both return the same WeatherResponse shape.
"""

import httpx
from datetime import date
from typing import Optional

from app.models.schemas import DailyWeather, WeatherResponse

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

DAILY_FIELDS = (
    "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
    "relative_humidity_2m_mean,precipitation_sum,wind_speed_10m_max"
)


class ForecastServiceError(Exception):
    pass


async def fetch_forecast(
    latitude: float,
    longitude: float,
    days: int = 5,
    location_name: Optional[str] = None,
) -> WeatherResponse:
    """
    Fetch a forward-looking daily forecast for the next `days` days (max 16).
    """
    days = max(1, min(days, 16))

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY_FIELDS,
        "forecast_days": days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(OPEN_METEO_BASE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise ForecastServiceError(f"Open-Meteo request failed: {e}") from e
        payload = resp.json()

    try:
        d = payload["daily"]
    except KeyError as e:
        raise ForecastServiceError(f"Unexpected Open-Meteo response shape: {payload}") from e

    daily_records = []
    for i, date_str in enumerate(d["time"]):
        y, m, day = (int(x) for x in date_str.split("-"))
        daily_records.append(
            DailyWeather(
                date=date(y, m, day),
                temp_avg_c=d["temperature_2m_mean"][i],
                temp_max_c=d["temperature_2m_max"][i],
                temp_min_c=d["temperature_2m_min"][i],
                humidity_pct=d["relative_humidity_2m_mean"][i],
                rainfall_mm=d["precipitation_sum"][i],
                wind_speed_ms=d["wind_speed_10m_max"][i],
                is_forecast=True,
            )
        )

    # Open-Meteo forecasts are essentially always complete for the requested window
    completeness = round((len(daily_records) / days) * 100, 1) if days > 0 else 0.0

    return WeatherResponse(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        daily=daily_records,
        source="OPEN_METEO_FORECAST",
        data_completeness_pct=completeness,
    )
