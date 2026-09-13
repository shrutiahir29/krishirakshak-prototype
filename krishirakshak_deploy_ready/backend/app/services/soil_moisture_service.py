"""
Soil Moisture Estimation Service
=================================
No physical soil sensor required. We run a simple daily "water balance"
simulation over a root-zone bucket:

    moisture(today) = moisture(yesterday) + rainfall - crop_ET

where crop_ET = ET0 (Hargreaves, temperature-only) x crop coefficient (Kc).
The bucket is bounded by [wilting_point, field_capacity]; anything above
field capacity is assumed to drain away (runoff/percolation).

This combines:
  - Recent HISTORICAL weather (NASA POWER) to establish where moisture
    likely stands today
  - FORECAST weather (Open-Meteo) to project moisture forward, which the
    irrigation advisory module uses for "skip if rain expected" logic

Caveat (documented, not hidden): this is a simplified single-layer bucket
model, not a full soil-physics model (e.g. no infiltration limits, no
capillary rise). It's a reasonable proxy for advisory purposes, and its
accuracy improves if a real soil test ever refines field_capacity/wilting_point.
"""

from datetime import date
from typing import List, Optional

from app.models.schemas import (
    DailyWeather,
    SoilProfile,
    DailySoilMoisture,
    SoilMoistureResponse,
)
from app.utils.evapotranspiration import hargreaves_eto_mm

# Assumed effective root-zone depth (mm of water storage capacity).
# 300mm is a reasonable default for shallow-to-medium rooted field crops.
ROOT_ZONE_DEPTH_MM = 300.0

# Default crop coefficient if none supplied (Kc=1.0 ~ generic reference crop)
DEFAULT_KC = 1.0


def _run_water_balance(
    latitude: float,
    days: List[DailyWeather],
    soil: SoilProfile,
    crop_coefficient: float,
) -> List[DailySoilMoisture]:
    moisture = soil.initial_moisture_pct if soil.initial_moisture_pct is not None else soil.field_capacity_pct
    results = []

    for day_weather in days:
        eto = hargreaves_eto_mm(
            latitude_deg=latitude,
            day=day_weather.date,
            temp_mean_c=day_weather.temp_avg_c,
            temp_max_c=day_weather.temp_max_c,
            temp_min_c=day_weather.temp_min_c,
        )
        etc = eto * crop_coefficient  # crop-adjusted water loss

        # Convert mm changes into % of root-zone bucket
        delta_pct = (day_weather.rainfall_mm - etc) / ROOT_ZONE_DEPTH_MM * 100
        moisture = moisture + delta_pct

        # Bound within [wilting_point, field_capacity] -- excess rain "drains off"
        moisture = max(soil.wilting_point_pct, min(soil.field_capacity_pct, moisture))

        results.append(
            DailySoilMoisture(
                date=day_weather.date,
                rainfall_mm=day_weather.rainfall_mm,
                eto_mm=round(eto, 2),
                moisture_pct=round(moisture, 1),
                is_forecast=day_weather.is_forecast,
            )
        )

    return results


def estimate_soil_moisture(
    latitude: float,
    longitude: float,
    historical_days: List[DailyWeather],
    forecast_days: List[DailyWeather],
    soil: Optional[SoilProfile] = None,
    crop_coefficient: float = DEFAULT_KC,
    historical_data_completeness_pct: float = 100.0,
) -> SoilMoistureResponse:
    """
    Run the water balance across historical days (to anchor current state)
    then continue into forecast days (to project forward).
    """
    soil = soil or SoilProfile()

    all_days = sorted(historical_days, key=lambda d: d.date) + sorted(forecast_days, key=lambda d: d.date)
    if not all_days:
        raise ValueError("No weather data provided to estimate soil moisture from.")

    daily_results = _run_water_balance(latitude, all_days, soil, crop_coefficient)

    # "Current" moisture = last historical (non-forecast) day, or first day if all forecast
    historical_results = [d for d in daily_results if not d.is_forecast]
    current = historical_results[-1].moisture_pct if historical_results else daily_results[0].moisture_pct

    # Confidence: driven primarily by how complete the underlying weather data was,
    # with a small penalty if we had to fall back to an assumed initial moisture.
    confidence = historical_data_completeness_pct
    if soil.initial_moisture_pct is None:
        confidence = max(0.0, confidence - 10.0)  # we guessed the starting point

    return SoilMoistureResponse(
        latitude=latitude,
        longitude=longitude,
        soil_profile=soil,
        daily=daily_results,
        current_moisture_pct=current,
        confidence_pct=round(confidence, 1),
    )
