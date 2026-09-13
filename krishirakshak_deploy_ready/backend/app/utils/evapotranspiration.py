"""
Evapotranspiration Utilities
=============================
Implements the FAO-56 Hargreaves method for estimating reference
evapotranspiration (ET0) using ONLY temperature data (no solar radiation
sensor, no pan evaporation station needed) — perfect for a sensor-free
farming platform.

Reference: Allen et al., FAO Irrigation and Drainage Paper 56.
"""

import math
from datetime import date

GSC = 0.0820  # solar constant, MJ m-2 min-1


def _extraterrestrial_radiation_mm(latitude_deg: float, day_of_year: int) -> float:
    """
    Ra: extraterrestrial radiation, converted to mm/day water-equivalent.
    Depends only on latitude and day-of-year (i.e. sun angle) — no sensor needed.
    """
    lat_rad = math.radians(latitude_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * day_of_year)  # inverse rel. earth-sun distance
    decl = 0.409 * math.sin(2 * math.pi / 365 * day_of_year - 1.39)  # solar declination

    # sunset hour angle (guard against domain errors at extreme latitudes)
    x = -math.tan(lat_rad) * math.tan(decl)
    x = max(-1.0, min(1.0, x))
    omega_s = math.acos(x)

    ra_mj = (
        (24 * 60 / math.pi)
        * GSC
        * dr
        * (omega_s * math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.sin(omega_s))
    )
    return 0.408 * ra_mj  # MJ/m2/day -> mm/day water-equivalent


def hargreaves_eto_mm(
    latitude_deg: float,
    day: date,
    temp_mean_c: float,
    temp_max_c: float,
    temp_min_c: float,
) -> float:
    """
    Hargreaves (1985) reference evapotranspiration, mm/day.
    ET0 = 0.0023 * Ra * (Tmean + 17.8) * sqrt(Tmax - Tmin)
    """
    ra = _extraterrestrial_radiation_mm(latitude_deg, day.timetuple().tm_yday)
    temp_range = max(temp_max_c - temp_min_c, 0)  # guard against bad data
    eto = 0.0023 * ra * (temp_mean_c + 17.8) * math.sqrt(temp_range)
    return max(eto, 0.0)
