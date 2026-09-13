"""
Soil Moisture Router
=====================
Orchestrates: fetch historical weather -> fetch forecast -> run water balance.
This is the pattern every downstream module (pest risk, irrigation) will follow:
combine weather_service + forecast_service, then apply domain logic.
"""

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import SoilMoistureResponse, SoilProfile
from app.services import weather_service, forecast_service, soil_moisture_service

router = APIRouter(prefix="/api/soil-moisture", tags=["soil-moisture"])


@router.get("/estimate", response_model=SoilMoistureResponse)
async def get_soil_moisture_estimate(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    history_days: int = Query(14, ge=3, le=60, description="Days of history to anchor current moisture"),
    forecast_days: int = Query(5, ge=1, le=16, description="Days to project forward"),
    soil_type: str = Query("loam"),
    field_capacity_pct: float = Query(35.0),
    wilting_point_pct: float = Query(15.0),
    crop_coefficient: float = Query(1.0, description="Kc; e.g. ~1.15 for rice mid-season, ~0.7 for early-stage cotton"),
):
    try:
        historical = await weather_service.fetch_recent_weather(latitude, longitude, days_back=history_days)
        forecast = await forecast_service.fetch_forecast(latitude, longitude, days=forecast_days)
    except (weather_service.WeatherServiceError, forecast_service.ForecastServiceError) as e:
        raise HTTPException(status_code=502, detail=str(e))

    soil = SoilProfile(
        soil_type=soil_type,
        field_capacity_pct=field_capacity_pct,
        wilting_point_pct=wilting_point_pct,
    )

    try:
        return soil_moisture_service.estimate_soil_moisture(
            latitude=latitude,
            longitude=longitude,
            historical_days=historical.daily,
            forecast_days=forecast.daily,
            soil=soil,
            crop_coefficient=crop_coefficient,
            historical_data_completeness_pct=historical.data_completeness_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
