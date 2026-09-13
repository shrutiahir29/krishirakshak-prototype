from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import CropRecommendationResponse
from app.services import weather_service, crop_recommendation_service

router = APIRouter(prefix="/api/crop-recommendation", tags=["crop-recommendation"])


@router.get("/rank", response_model=CropRecommendationResponse)
async def get_crop_recommendations(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    history_days: int = Query(30, ge=7, le=90, description="Averages weather over this window"),
    top_n: int = Query(5, ge=1, le=10),
):
    try:
        historical = await weather_service.fetch_recent_weather(latitude, longitude, days_back=history_days)
    except weather_service.WeatherServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if not historical.daily:
        raise HTTPException(status_code=422, detail="No weather data available to base recommendation on.")

    n = len(historical.daily)
    avg_temp = sum(d.temp_avg_c for d in historical.daily) / n
    avg_humidity = sum(d.humidity_pct for d in historical.daily) / n
    total_rain = sum(d.rainfall_mm for d in historical.daily)
    # normalize rainfall to a "per month" figure regardless of the window queried
    rainfall_per_month = total_rain / n * 30

    return crop_recommendation_service.recommend_crops(
        avg_temp_c=avg_temp,
        avg_humidity_pct=avg_humidity,
        avg_rainfall_mm_month=rainfall_per_month,
        top_n=top_n,
    )
