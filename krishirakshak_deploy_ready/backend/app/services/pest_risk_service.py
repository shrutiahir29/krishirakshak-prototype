"""
Pest Risk Forecasting Service
===============================
Rule-based 0-100 scoring engine. Each pest has a small "profile" of the
weather conditions that favor it (temperature band, humidity threshold,
consecutive wet/dry days, etc.), sourced from standard agricultural
extension guidelines (ICAR / state agri-department pest advisories).

This is intentionally a swappable module: `PEST_PROFILES` below is a plain
data structure. Feed in real historical outbreak+weather data later and this
can be replaced/calibrated (e.g. logistic regression on outbreak labels)
without touching the router or response shape.
"""

from typing import List, Dict
from datetime import date

from app.models.schemas import DailyWeather, DailyPestRisk, PestRiskFactor, PestRiskResponse

# Each pest profile: favorable temp range, favorable humidity floor,
# and whether it likes consecutive wet or dry spells.
PEST_PROFILES: Dict[str, dict] = {
    "cotton": {
        "pest_name": "Bollworm (Helicoverpa armigera)",
        "temp_min": 25, "temp_max": 35,
        "humidity_threshold": 65,
        "prefers": "dry_spell_then_humid",  # bollworm thrives after a dry spell + rising humidity
    },
    "rice": {
        "pest_name": "Brown Planthopper",
        "temp_min": 25, "temp_max": 30,
        "humidity_threshold": 80,
        "prefers": "wet_spell",
    },
    "soybean": {
        "pest_name": "Girdle Beetle",
        "temp_min": 25, "temp_max": 32,
        "humidity_threshold": 70,
        "prefers": "wet_spell",
    },
    "wheat": {
        "pest_name": "Aphids",
        "temp_min": 15, "temp_max": 22,
        "humidity_threshold": 60,
        "prefers": "cool_humid",
    },
}

DEFAULT_PROFILE = {
    "pest_name": "Generic foliar pest/disease pressure",
    "temp_min": 22, "temp_max": 32,
    "humidity_threshold": 70,
    "prefers": "wet_spell",
}


def _risk_level(score: float) -> str:
    if score >= 75:
        return "Severe"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Low"


def _score_day(
    day: DailyWeather,
    profile: dict,
    recent_days: List[DailyWeather],
) -> DailyPestRisk:
    factors: List[PestRiskFactor] = []
    score = 0.0

    # Factor 1: Temperature favorability (0-35 pts)
    if profile["temp_min"] <= day.temp_avg_c <= profile["temp_max"]:
        pts = 35.0
        factors.append(PestRiskFactor(
            name="Temperature",
            contribution=pts,
            reason=f"{day.temp_avg_c:.1f}\u00b0C is within the {profile['temp_min']}-{profile['temp_max']}\u00b0C favorable range",
        ))
    else:
        # Partial credit that decays with distance from the favorable band
        dist = min(abs(day.temp_avg_c - profile["temp_min"]), abs(day.temp_avg_c - profile["temp_max"]))
        pts = max(0.0, 35.0 - dist * 5)
        if pts > 0:
            factors.append(PestRiskFactor(
                name="Temperature",
                contribution=round(pts, 1),
                reason=f"{day.temp_avg_c:.1f}\u00b0C is close to, but outside, the favorable range",
            ))
    score += pts

    # Factor 2: Humidity favorability (0-35 pts)
    if day.humidity_pct >= profile["humidity_threshold"]:
        pts = 35.0
        factors.append(PestRiskFactor(
            name="Humidity",
            contribution=pts,
            reason=f"{day.humidity_pct:.0f}% humidity meets/exceeds the {profile['humidity_threshold']}% threshold",
        ))
    else:
        pts = max(0.0, 35.0 - (profile["humidity_threshold"] - day.humidity_pct) * 1.5)
        if pts > 0:
            factors.append(PestRiskFactor(
                name="Humidity",
                contribution=round(pts, 1),
                reason=f"{day.humidity_pct:.0f}% humidity is below threshold but not far off",
            ))
    score += pts

    # Factor 3: Recent rainfall pattern (0-30 pts) - depends on what this pest "prefers"
    recent_rain_days = sum(1 for d in recent_days if d.rainfall_mm > 2.0)
    recent_dry_days = sum(1 for d in recent_days if d.rainfall_mm <= 2.0)

    if profile["prefers"] in ("wet_spell", "cool_humid") and recent_rain_days >= 2:
        pts = min(30.0, recent_rain_days * 6)
        factors.append(PestRiskFactor(
            name="Rainfall pattern",
            contribution=round(pts, 1),
            reason=f"{recent_rain_days} wet day(s) in the last {len(recent_days)} days favor this pest",
        ))
        score += pts
    elif profile["prefers"] == "dry_spell_then_humid" and recent_dry_days >= 3 and day.humidity_pct >= profile["humidity_threshold"] - 10:
        pts = min(30.0, recent_dry_days * 5)
        factors.append(PestRiskFactor(
            name="Rainfall pattern",
            contribution=round(pts, 1),
            reason=f"{recent_dry_days} dry day(s) followed by rising humidity is a classic trigger",
        ))
        score += pts

    score = round(min(score, 100.0), 1)

    return DailyPestRisk(
        date=day.date,
        risk_score=score,
        risk_level=_risk_level(score),
        pest_name=profile["pest_name"],
        factors=factors,
    )


def forecast_pest_risk(
    crop: str,
    latitude: float,
    longitude: float,
    historical_days: List[DailyWeather],
    forecast_days: List[DailyWeather],
    historical_data_completeness_pct: float = 100.0,
) -> PestRiskResponse:
    profile = PEST_PROFILES.get(crop.lower(), DEFAULT_PROFILE)

    all_days = sorted(historical_days, key=lambda d: d.date) + sorted(forecast_days, key=lambda d: d.date)
    daily_results = []

    for i, day in enumerate(all_days):
        # look back up to 5 days for pattern detection
        lookback = all_days[max(0, i - 5):i]
        daily_results.append(_score_day(day, profile, lookback))

    # Only surface the forecast window (3-5 days ahead) as the headline result,
    # but we keep history in daily_results so the frontend can chart the trend too.
    return PestRiskResponse(
        crop=crop,
        latitude=latitude,
        longitude=longitude,
        daily=daily_results,
        confidence_pct=round(historical_data_completeness_pct, 1),
    )
