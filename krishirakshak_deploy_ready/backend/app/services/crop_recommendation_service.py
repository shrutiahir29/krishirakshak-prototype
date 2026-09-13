"""
Crop Recommendation Service
==============================
Rule-based suitability scoring (v1). Compares current field conditions
(avg temp, humidity, rainfall, soil moisture) against each crop's ideal
requirement ranges and produces a 0-100 suitability score per crop.

Upgrade path (documented, not built yet): once a labeled crop-recommendation
dataset is available (e.g. the common Kaggle "Crop_recommendation.csv" with
N/P/K, temperature, humidity, pH, rainfall -> crop label), swap this
function's internals for a trained Random Forest / Decision Tree classifier.
The router/response shape won't need to change.
"""

from typing import List
from app.models.schemas import CropSuitability, CropRecommendationResponse

# crop: (temp_min, temp_max, humidity_min, humidity_max, rainfall_min_mm_per_month, rainfall_max_mm_per_month)
CROP_REQUIREMENTS = {
    "cotton":  {"temp": (21, 35), "humidity": (50, 80), "rainfall_mm_month": (50, 150)},
    "rice":    {"temp": (20, 35), "humidity": (70, 90), "rainfall_mm_month": (150, 300)},
    "soybean": {"temp": (20, 32), "humidity": (60, 85), "rainfall_mm_month": (80, 200)},
    "wheat":   {"temp": (10, 25), "humidity": (40, 70), "rainfall_mm_month": (30, 100)},
    "sugarcane": {"temp": (21, 38), "humidity": (65, 85), "rainfall_mm_month": (100, 250)},
    "gram (chana)": {"temp": (15, 28), "humidity": (30, 60), "rainfall_mm_month": (20, 80)},
}


def _band_score(value: float, low: float, high: float) -> float:
    """100 if within [low, high], decaying linearly outside it."""
    if low <= value <= high:
        return 100.0
    span = high - low if high > low else 1.0
    dist = (low - value) if value < low else (value - high)
    return max(0.0, 100.0 - (dist / span) * 100.0)


def recommend_crops(
    avg_temp_c: float,
    avg_humidity_pct: float,
    avg_rainfall_mm_month: float,
    soil_moisture_pct: float | None = None,
    top_n: int = 5,
) -> CropRecommendationResponse:
    results: List[CropSuitability] = []

    for crop, req in CROP_REQUIREMENTS.items():
        temp_score = _band_score(avg_temp_c, *req["temp"])
        humidity_score = _band_score(avg_humidity_pct, *req["humidity"])
        rainfall_score = _band_score(avg_rainfall_mm_month, *req["rainfall_mm_month"])

        overall = round((temp_score * 0.4 + humidity_score * 0.3 + rainfall_score * 0.3), 1)

        reasons = []
        reasons.append(
            f"Temperature {avg_temp_c:.1f}\u00b0C vs ideal {req['temp'][0]}-{req['temp'][1]}\u00b0C "
            f"({'good fit' if temp_score >= 70 else 'suboptimal'})"
        )
        reasons.append(
            f"Humidity {avg_humidity_pct:.0f}% vs ideal {req['humidity'][0]}-{req['humidity'][1]}% "
            f"({'good fit' if humidity_score >= 70 else 'suboptimal'})"
        )
        reasons.append(
            f"Rainfall {avg_rainfall_mm_month:.0f}mm/month vs ideal {req['rainfall_mm_month'][0]}-{req['rainfall_mm_month'][1]}mm "
            f"({'good fit' if rainfall_score >= 70 else 'suboptimal'})"
        )

        results.append(CropSuitability(crop=crop.title(), suitability_score=overall, reasons=reasons))

    results.sort(key=lambda c: c.suitability_score, reverse=True)

    # Confidence: simple v1 heuristic - fewer inputs / defaults used -> lower confidence.
    confidence = 85.0 if soil_moisture_pct is not None else 75.0

    return CropRecommendationResponse(ranked_crops=results[:top_n], confidence_pct=confidence)
