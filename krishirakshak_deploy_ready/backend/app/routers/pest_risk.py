from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import PestRiskResponse
from app.services import weather_service, forecast_service, pest_risk_service

router = APIRouter(prefix="/api/pest-risk", tags=["pest-risk"])


@router.get("/forecast", response_model=PestRiskResponse)
async def get_pest_risk_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    crop: str = Query("cotton"),
    history_days: int = Query(10, ge=5, le=30),
    forecast_days: int = Query(5, ge=1, le=10),
):
    try:
        historical = await weather_service.fetch_recent_weather(latitude, longitude, days_back=history_days)
        forecast = await forecast_service.fetch_forecast(latitude, longitude, days=forecast_days)
    except (weather_service.WeatherServiceError, forecast_service.ForecastServiceError) as e:
        raise HTTPException(status_code=502, detail=str(e))

    return pest_risk_service.forecast_pest_risk(
        crop=crop,
        latitude=latitude,
        longitude=longitude,
        historical_days=historical.daily,
        forecast_days=forecast.daily,
        historical_data_completeness_pct=historical.data_completeness_pct,
    )
