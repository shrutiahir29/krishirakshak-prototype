"""
Shared data models (Pydantic schemas) used across the API.
Keeping these in one place means every service/router speaks the same 'language'.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class DailyWeather(BaseModel):
    """One day's weather observation or forecast."""
    date: date
    temp_avg_c: float
    temp_max_c: float
    temp_min_c: float
    humidity_pct: float
    rainfall_mm: float
    wind_speed_ms: float
    is_forecast: bool = False  # True if this is a predicted/future value


class WeatherResponse(BaseModel):
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    daily: List[DailyWeather]
    source: str = "NASA_POWER"
    data_completeness_pct: float = Field(
        ..., description="Percent of expected days that had valid data (drives confidence score)"
    )


class LocationQuery(BaseModel):
    latitude: float
    longitude: float
    location_name: Optional[str] = None


class SoilProfile(BaseModel):
    """
    Simplified soil-type parameters that bound how much water the soil can hold.
    Values are volumetric water content (%) — defaults are reasonable loam values;
    can be refined per soil type (sandy/clay/loam) later.
    """
    soil_type: str = "loam"
    field_capacity_pct: float = Field(35.0, description="Max moisture soil can hold against gravity")
    wilting_point_pct: float = Field(15.0, description="Moisture below which plants can't extract water")
    initial_moisture_pct: Optional[float] = Field(
        None, description="Known starting moisture, if available. Otherwise estimated at field_capacity."
    )


class DailySoilMoisture(BaseModel):
    date: date
    rainfall_mm: float
    eto_mm: float = Field(..., description="Reference evapotranspiration (Hargreaves estimate)")
    moisture_pct: float
    is_forecast: bool = False


class SoilMoistureResponse(BaseModel):
    latitude: float
    longitude: float
    soil_profile: SoilProfile
    daily: List[DailySoilMoisture]
    current_moisture_pct: float
    confidence_pct: float = Field(
        ..., description="Confidence in the estimate, driven by weather data completeness/recency"
    )


# ---------------- Pest Risk ----------------

class PestRiskFactor(BaseModel):
    name: str
    contribution: float = Field(..., description="Points (0-100 scale) this factor added to the score")
    reason: str


class DailyPestRisk(BaseModel):
    date: date
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str  # "Low" | "Moderate" | "High" | "Severe"
    pest_name: str
    factors: List[PestRiskFactor]


class PestRiskResponse(BaseModel):
    crop: str
    latitude: float
    longitude: float
    daily: List[DailyPestRisk]
    confidence_pct: float


# ---------------- Irrigation Advisory ----------------

class IrrigationAdvice(BaseModel):
    should_irrigate: bool
    irrigation_intensity_pct: float = Field(..., ge=0, le=100, description="How much of a full irrigation dose is needed")
    reason: str
    current_moisture_pct: float
    ideal_moisture_range: List[float]
    rain_expected_next_2_days_mm: float
    estimated_water_saved_liters_per_acre: float
    confidence_pct: float


# ---------------- Crop Recommendation ----------------

class CropSuitability(BaseModel):
    crop: str
    suitability_score: float = Field(..., ge=0, le=100)
    reasons: List[str]


class CropRecommendationResponse(BaseModel):
    ranked_crops: List[CropSuitability]
    confidence_pct: float


# ---------------- Disease Detection & Treatment ----------------

class DiseaseDetectionResult(BaseModel):
    detected_problem: str
    confidence_pct: float
    recommended_treatment: str
    treatment_timing: str
    historical_context: Optional[str] = None
