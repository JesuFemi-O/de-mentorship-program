"""
Weather data generation for GreenVault markets.

Produces deterministic daily weather snapshots per market based on
Nigerian regional climate patterns. Same date + market always produces
the same result — critical for learner reproducibility.

Adapted from the GreenVault world-building model with two key changes:
- random.random() replaced with hashlib seeding (deterministic)
- Scoped to the 5 markets used in Chapter 1
"""

import hashlib
from datetime import datetime
from typing import Optional, TypedDict


class WeatherRecord(TypedDict):
    date: str
    market_id: str
    region: str
    season: str                          # "rainy" or "dry"
    temperature_c: float
    humidity_percent: float
    rainfall_mm: float
    wind_speed_kmh: float
    wind_direction: str
    sunshine_hours: float
    cloud_cover_percent: float
    harmattan_active: bool
    dust_intensity: Optional[str]        # "light", "moderate", "heavy" — null when harmattan_active is False
    visibility_km: Optional[float]       # null when harmattan_active is False
    air_quality_index: Optional[int]     # null when harmattan_active is False


# Maps each market to its Nigerian climate region
MARKET_REGIONS = {
    "lagos_lekki": "south_coastal",
    "makurdi_central": "middle_belt",
    "jos_main": "middle_belt",
    "kaduna_central": "middle_belt",
    "kano_central": "north",
}

# Climate definitions per region and season.
# rain_prob: fraction of days in the month that see rain.
# rain_intensity: (min_mm, max_mm) on a rainy day.
REGIONAL_CLIMATES = {
    "south_coastal": {
        "display": "South Coastal",
        "seasons": {
            "rainy": {
                "months": [3, 4, 5, 6, 7, 8, 9, 10, 11],
                "temp": (23.0, 30.0),
                "humidity": (75.0, 95.0),
                "rain_prob": 20 / 30,
                "rain_intensity": (10.0, 120.0),
                "wind_speed": (10.0, 25.0),
                "wind_dir": "SW",
                "sunshine_hours": 4.5,
                "cloud_cover": (60.0, 90.0),
            },
            "dry": {
                "months": [12, 1, 2],
                "temp": (25.0, 34.0),
                "humidity": (50.0, 70.0),
                "rain_prob": 2 / 30,
                "rain_intensity": (2.0, 20.0),
                "wind_speed": (12.0, 30.0),
                "wind_dir": "NE",
                "sunshine_hours": 8.0,
                "cloud_cover": (20.0, 40.0),
                "harmattan": {
                    "months": [12, 1, 2],
                    "dust_intensity": "light",
                    "visibility_km": (5.0, 10.0),
                    "air_quality_index": (50, 100),
                },
            },
        },
    },
    "middle_belt": {
        "display": "Middle Belt",
        "seasons": {
            "rainy": {
                "months": [4, 5, 6, 7, 8, 9, 10],
                "temp": (21.0, 30.0),
                "humidity": (60.0, 80.0),
                "rain_prob": 15 / 30,
                "rain_intensity": (8.0, 90.0),
                "wind_speed": (10.0, 22.0),
                "wind_dir": "SW",
                "sunshine_hours": 5.5,
                "cloud_cover": (50.0, 75.0),
            },
            "dry": {
                "months": [11, 12, 1, 2, 3],
                "temp": (20.0, 38.0),
                "humidity": (20.0, 45.0),
                "rain_prob": 0,
                "rain_intensity": (0.0, 5.0),
                "wind_speed": (15.0, 35.0),
                "wind_dir": "NE",
                "sunshine_hours": 9.5,
                "cloud_cover": (5.0, 25.0),
                "harmattan": {
                    "months": [12, 1, 2],
                    "dust_intensity": "moderate",
                    "visibility_km": (2.0, 6.0),
                    "air_quality_index": (100, 150),
                },
            },
        },
    },
    "north": {
        "display": "North",
        "seasons": {
            "rainy": {
                "months": [5, 6, 7, 8, 9],
                "temp": (24.0, 34.0),
                "humidity": (45.0, 70.0),
                "rain_prob": 12 / 30,
                "rain_intensity": (5.0, 70.0),
                "wind_speed": (12.0, 28.0),
                "wind_dir": "SW",
                "sunshine_hours": 6.5,
                "cloud_cover": (40.0, 65.0),
            },
            "dry": {
                "months": [10, 11, 12, 1, 2, 3, 4],
                "temp": (18.0, 42.0),
                "humidity": (10.0, 30.0),
                "rain_prob": 0,
                "rain_intensity": (0.0, 2.0),
                "wind_speed": (15.0, 45.0),
                "wind_dir": "NE",
                "sunshine_hours": 10.5,
                "cloud_cover": (5.0, 15.0),
                "harmattan": {
                    "months": [12, 1, 2],
                    "dust_intensity": "heavy",
                    "visibility_km": (0.5, 4.0),
                    "air_quality_index": (150, 250),
                },
            },
        },
    },
}


def _seeded_value(date: str, market: str, field: str, min_val: float, max_val: float) -> float:
    """Deterministic value in [min_val, max_val]. Same inputs always produce the same output."""
    key = f"{date}:{market}:{field}:42".encode()
    hash_int = int(hashlib.md5(key).hexdigest(), 16)
    ratio = (hash_int % 10000) / 10000.0
    return round(min_val + ratio * (max_val - min_val), 1)


def _get_season(region_key: str, month: int) -> str:
    """Return 'rainy' or 'dry' for a given region and month."""
    for season_name, config in REGIONAL_CLIMATES[region_key]["seasons"].items():
        if month in config["months"]:
            return season_name
    return "dry"


def generate_weather(date: str, market_id: str) -> WeatherRecord:
    """
    Generate a deterministic weather snapshot for a market on a given date.

    Args:
        date: ISO8601 date string (e.g., "2026-05-08")
        market_id: Market identifier (must be in MARKET_REGIONS)

    Returns:
        WeatherRecord. Harmattan fields (dust_intensity, visibility_km,
        air_quality_index) are null unless harmattan_active is True.
    """
    region_key = MARKET_REGIONS[market_id]
    climate = REGIONAL_CLIMATES[region_key]
    month = datetime.fromisoformat(date).month
    season_name = _get_season(region_key, month)
    season = climate["seasons"][season_name]

    # Deterministic rainfall: decide if it rains today, then how much
    rain_roll = _seeded_value(date, market_id, "rain_roll", 0.0, 1.0)
    if rain_roll < season["rain_prob"]:
        rainfall = _seeded_value(date, market_id, "rainfall", *season["rain_intensity"])
    else:
        rainfall = 0.0

    record: WeatherRecord = {
        "date": date,
        "market_id": market_id,
        "region": climate["display"],
        "season": season_name,
        "temperature_c": _seeded_value(date, market_id, "temperature", *season["temp"]),
        "humidity_percent": _seeded_value(date, market_id, "humidity", *season["humidity"]),
        "rainfall_mm": rainfall,
        "wind_speed_kmh": _seeded_value(date, market_id, "wind_speed", *season["wind_speed"]),
        "wind_direction": season["wind_dir"],
        "sunshine_hours": season["sunshine_hours"],
        "cloud_cover_percent": _seeded_value(date, market_id, "cloud_cover", *season["cloud_cover"]),
        "harmattan_active": False,
        "dust_intensity": None,
        "visibility_km": None,
        "air_quality_index": None,
    }

    harmattan_config = season.get("harmattan")
    if harmattan_config and month in harmattan_config["months"]:
        record["harmattan_active"] = True
        record["dust_intensity"] = harmattan_config["dust_intensity"]
        record["visibility_km"] = _seeded_value(
            date, market_id, "visibility", *harmattan_config["visibility_km"]
        )
        record["air_quality_index"] = int(
            _seeded_value(
                date, market_id, "aqi",
                float(harmattan_config["air_quality_index"][0]),
                float(harmattan_config["air_quality_index"][1]),
            )
        )

    return record


def get_weather_modifier(weather: WeatherRecord) -> float:
    """
    Calculate a price modifier based on weather conditions.

    Heavy rain disrupts road transport to market; Harmattan dust reduces
    visibility and slows logistics — both push commodity prices up.

    Returns:
        Multiplier applied to commodity prices (1.0 = no change).
    """
    modifier = 1.0

    if weather["rainfall_mm"] > 50:
        modifier *= 1.05
    elif weather["rainfall_mm"] > 25:
        modifier *= 1.02

    if weather["harmattan_active"]:
        dust = weather["dust_intensity"]
        if dust == "heavy":
            modifier *= 1.06
        elif dust == "moderate":
            modifier *= 1.03
        else:
            modifier *= 1.01

    return round(modifier, 4)
