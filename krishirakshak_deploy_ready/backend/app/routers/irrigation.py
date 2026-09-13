from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import IrrigationAdvice, SoilProfile
from app.services import weather_service, forecast_service, soil_moisture_service, irrigation_service

router = APIRouter(prefix="/api/irrigation", tags=["irrigation"])


@router.get("/advice", response_model=IrrigationAdvice)
async def get_irrigation_advice(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    crop: str = Query("cotton"),
    history_days: int = Query(14, ge=3, le=60),
    forecast_days: int = Query(5, ge=1, le=16),
    field_capacity_pct: float = Query(35.0),
    wilting_point_pct: float = Query(15.0),
    crop_coefficient: float = Query(1.0),
):
    try:
        historical = await weather_service.fetch_recent_weather(latitude, longitude, days_back=history_days)
        forecast = await forecast_service.fetch_forecast(latitude, longitude, days=forecast_days)
    except (weather_service.WeatherServiceError, forecast_service.ForecastServiceError) as e:
        raise HTTPException(status_code=502, detail=str(e))

    soil = SoilProfile(field_capacity_pct=field_capacity_pct, wilting_point_pct=wilting_point_pct)
    moisture = soil_moisture_service.estimate_soil_moisture(
        latitude=latitude,
        longitude=longitude,
        historical_days=historical.daily,
        forecast_days=forecast.daily,
        soil=soil,
        crop_coefficient=crop_coefficient,
        historical_data_completeness_pct=historical.data_completeness_pct,
    )

    return irrigation_service.get_irrigation_advice(
        crop=crop,
        current_moisture_pct=moisture.current_moisture_pct,
        forecast_days=forecast.daily,
        moisture_confidence_pct=moisture.confidence_pct,
    )
