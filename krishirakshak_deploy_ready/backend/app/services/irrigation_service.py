"""
Irrigation Advisory Service
=============================
Combines soil moisture estimate + crop's ideal moisture range + next-2-day
rain forecast into a single actionable recommendation.

Logic:
  1. If moisture is already within/above ideal range -> skip.
  2. If moisture is below ideal AND meaningful rain (>=10mm) is expected in
     the next 2 days -> skip, rain will likely cover it.
  3. Otherwise -> irrigate, with intensity proportional to the moisture
     deficit below the ideal range's midpoint.

Water saved is estimated only for the "skip because rain is coming" case -
that's water that would have been pumped/used unnecessarily.
"""

from typing import List, Tuple

from app.models.schemas import DailySoilMoisture, DailyWeather, IrrigationAdvice

# Ideal moisture range (%) per crop - standard agronomic guidance.
# Falls back to a generic range if crop isn't listed.
CROP_IDEAL_MOISTURE: dict = {
    "cotton": (25, 32),
    "rice": (30, 38),  # rice tolerates/needs wetter soil
    "soybean": (22, 30),
    "wheat": (20, 28),
}
DEFAULT_IDEAL_MOISTURE = (22, 30)

RAIN_SKIP_THRESHOLD_MM = 10.0  # forecasted rain at/above this -> likely enough, skip irrigation

# Rough assumption for water-saved estimation: a "full" irrigation dose
# is ~25mm depth, and 1mm over 1 acre ~ 4,047 liters.
FULL_DOSE_MM = 25.0
LITERS_PER_MM_PER_ACRE = 4047.0


def _next_2_day_rain(forecast_days: List[DailyWeather]) -> float:
    sorted_days = sorted(forecast_days, key=lambda d: d.date)
    return sum(d.rainfall_mm for d in sorted_days[:2])


def get_irrigation_advice(
    crop: str,
    current_moisture_pct: float,
    forecast_days: List[DailyWeather],
    moisture_confidence_pct: float,
) -> IrrigationAdvice:
    ideal_low, ideal_high = CROP_IDEAL_MOISTURE.get(crop.lower(), DEFAULT_IDEAL_MOISTURE)
    rain_next_2d = round(_next_2_day_rain(forecast_days), 1)

    # Case 1: already sufficiently moist
    if current_moisture_pct >= ideal_low:
        return IrrigationAdvice(
            should_irrigate=False,
            irrigation_intensity_pct=0.0,
            reason=f"Soil moisture ({current_moisture_pct:.1f}%) is already at/above the ideal minimum ({ideal_low}%) for {crop}.",
            current_moisture_pct=current_moisture_pct,
            ideal_moisture_range=[ideal_low, ideal_high],
            rain_expected_next_2_days_mm=rain_next_2d,
            estimated_water_saved_liters_per_acre=0.0,
            confidence_pct=moisture_confidence_pct,
        )

    deficit = ideal_low - current_moisture_pct
    band_width = max(ideal_high - ideal_low, 1.0)
    # Scale: a deficit equal to the full ideal band width -> 100% dose. Smaller deficits scale down, floor at 10%.
    intensity = round(min(100.0, max(10.0, (deficit / band_width) * 100)), 1)

    # Case 2: dry, but enough rain is coming -> skip and save water
    if rain_next_2d >= RAIN_SKIP_THRESHOLD_MM:
        water_saved = round((intensity / 100.0) * FULL_DOSE_MM * LITERS_PER_MM_PER_ACRE, 0)
        return IrrigationAdvice(
            should_irrigate=False,
            irrigation_intensity_pct=0.0,
            reason=(
                f"Soil is dry ({current_moisture_pct:.1f}%, below ideal {ideal_low}%), but "
                f"{rain_next_2d:.1f}mm of rain is forecast in the next 2 days — likely sufficient, so irrigation is skipped."
            ),
            current_moisture_pct=current_moisture_pct,
            ideal_moisture_range=[ideal_low, ideal_high],
            rain_expected_next_2_days_mm=rain_next_2d,
            estimated_water_saved_liters_per_acre=water_saved,
            confidence_pct=moisture_confidence_pct,
        )

    # Case 3: dry and no rain relief -> irrigate
    return IrrigationAdvice(
        should_irrigate=True,
        irrigation_intensity_pct=intensity,
        reason=(
            f"Soil moisture ({current_moisture_pct:.1f}%) is below the ideal range ({ideal_low}-{ideal_high}%) for {crop}, "
            f"and only {rain_next_2d:.1f}mm rain is expected in the next 2 days — irrigation recommended."
        ),
        current_moisture_pct=current_moisture_pct,
        ideal_moisture_range=[ideal_low, ideal_high],
        rain_expected_next_2_days_mm=rain_next_2d,
        estimated_water_saved_liters_per_acre=0.0,
        confidence_pct=moisture_confidence_pct,
    )
