"""
Weather Router
==============
Exposes weather + forecast data over HTTP so the React frontend (and other
backend modules like pest-risk/irrigation) can consume it.
"""

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import WeatherResponse
from app.services import weather_service, forecast_service

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/historical", response_model=WeatherResponse)
async def get_historical_weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days_back: int = Query(14, ge=1, le=90, description="How many days of history to fetch"),
    location_name: str | None = None,
):
    """Recent historical weather (source: NASA POWER)."""
    try:
        return await weather_service.fetch_recent_weather(
            latitude, longitude, days_back=days_back, location_name=location_name
        )
    except weather_service.WeatherServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/forecast", response_model=WeatherResponse)
async def get_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days: int = Query(5, ge=1, le=16, description="How many days ahead to forecast"),
    location_name: str | None = None,
):
    """Forward-looking forecast (source: Open-Meteo)."""
    try:
        return await forecast_service.fetch_forecast(
            latitude, longitude, days=days, location_name=location_name
        )
    except forecast_service.ForecastServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
