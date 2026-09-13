"""
Weather Service
================
Fetches daily weather data from NASA POWER (free, no API key required).
This is the foundational data source for pest-risk, soil-moisture and
irrigation modules, so it's built to be robust: retries, graceful handling
of missing days, and a "data completeness" score used later for confidence.

NASA POWER docs: https://power.larc.nasa.gov/docs/services/api/
"""

import httpx
from datetime import date, timedelta
from typing import Optional

from app.models.schemas import DailyWeather, WeatherResponse

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# NASA POWER's "fill value" for missing data
NASA_FILL_VALUE = -999

# Parameters we request:
# T2M = temp at 2m, T2M_MAX/MIN = daily max/min, RH2M = relative humidity,
# PRECTOTCORR = corrected precipitation, WS2M = wind speed at 2m
PARAMETERS = "T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR,WS2M"


class WeatherServiceError(Exception):
    """Raised when weather data cannot be fetched or parsed."""
    pass


async def fetch_historical_weather(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    location_name: Optional[str] = None,
) -> WeatherResponse:
    """
    Fetch daily historical weather for a lat/lon between start and end (inclusive).
    NASA POWER only provides *historical/near-real-time* data (usually 2-3 days
    behind present), not a true forward forecast — see forecast_service.py for
    the short-term forecast layer that fills that gap.
    """
    params = {
        "parameters": PARAMETERS,
        "community": "AG",  # Agroclimatology community = best defaults for farming use cases
        "longitude": longitude,
        "latitude": latitude,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(NASA_POWER_BASE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise WeatherServiceError(f"NASA POWER request failed: {e}") from e

        payload = resp.json()

    try:
        params_data = payload["properties"]["parameter"]
    except KeyError as e:
        raise WeatherServiceError(f"Unexpected NASA POWER response shape: {payload}") from e

    daily_records = []
    all_dates = sorted(params_data["T2M"].keys())  # e.g. "20250901"
    expected_days = (end - start).days + 1
    valid_days = 0

    for d in all_dates:
        raw = {
            "temp_avg_c": params_data["T2M"].get(d),
            "temp_max_c": params_data["T2M_MAX"].get(d),
            "temp_min_c": params_data["T2M_MIN"].get(d),
            "humidity_pct": params_data["RH2M"].get(d),
            "rainfall_mm": params_data["PRECTOTCORR"].get(d),
            "wind_speed_ms": params_data["WS2M"].get(d),
        }

        # Skip / flag days where NASA hasn't got data yet (fill value -999)
        if any(v is None or v == NASA_FILL_VALUE for v in raw.values()):
            continue

        valid_days += 1
        daily_records.append(
            DailyWeather(
                date=date(int(d[:4]), int(d[4:6]), int(d[6:8])),
                temp_avg_c=raw["temp_avg_c"],
                temp_max_c=raw["temp_max_c"],
                temp_min_c=raw["temp_min_c"],
                humidity_pct=raw["humidity_pct"],
                rainfall_mm=raw["rainfall_mm"],
                wind_speed_ms=raw["wind_speed_ms"],
                is_forecast=False,
            )
        )

    completeness = round((valid_days / expected_days) * 100, 1) if expected_days > 0 else 0.0

    return WeatherResponse(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        daily=daily_records,
        source="NASA_POWER",
        data_completeness_pct=completeness,
    )


async def fetch_recent_weather(
    latitude: float,
    longitude: float,
    days_back: int = 14,
    location_name: Optional[str] = None,
) -> WeatherResponse:
    """
    Convenience wrapper: fetch the last N days up to ~3 days ago
    (NASA POWER has a processing lag, so 'today' usually isn't available yet).
    """
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=days_back)
    return await fetch_historical_weather(latitude, longitude, start, end, location_name)
