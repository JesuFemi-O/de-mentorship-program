"""
Market price generation with reproducible seasonality, regional variance,
and weather-driven volatility.
"""

import hashlib
from datetime import datetime, timedelta
from typing import TypedDict

from weather_data import generate_weather, get_weather_modifier


class PriceRecord(TypedDict):
    commodity_id: str
    commodity_name: str
    unit: str
    unit_price_ngn: float
    recorded_at: str


class MarketRecordType(TypedDict):
    id: str
    name: str
    region: str
    lat: float
    lon: float
    regional_multiplier: float


# Base prices (median, before seasonality)
COMMODITY_BASE_PRICES = {
    "cassava_dried": 150.0,
    "maize_dried": 200.0,
    "honey_beans": 600.0,
    "yam": 1000.0,
    "groundnuts": 800.0,
    "millet": 250.0,
    "sorghum": 220.0,
    "rice": 450.0,
}

# Market metadata
MARKETS: dict[str, MarketRecordType] = {
    "lagos_lekki": {
        "id": "lagos_lekki",
        "name": "Lekki Market",
        "region": "Lagos",
        "lat": 6.4651,
        "lon": 3.5897,
        "regional_multiplier": 1.0,  # baseline
    },
    "makurdi_central": {
        "id": "makurdi_central",
        "name": "Makurdi Central Market",
        "region": "Middle Belt",
        "lat": 7.7411,
        "lon": 8.6753,
        "regional_multiplier": 0.95,  # slightly cheaper
    },
    "jos_main": {
        "id": "jos_main",
        "name": "Jos Main Market",
        "region": "Middle Belt",
        "lat": 9.9241,
        "lon": 8.8936,
        "regional_multiplier": 0.97,
    },
    "kaduna_central": {
        "id": "kaduna_central",
        "name": "Kaduna Central Market",
        "region": "Middle Belt",
        "lat": 10.5261,
        "lon": 7.4387,
        "regional_multiplier": 0.96,
    },
    "kano_central": {
        "id": "kano_central",
        "name": "Kano Central Market",
        "region": "North",
        "lat": 12.0022,
        "lon": 8.5920,
        "regional_multiplier": 0.90,  # Major northern production hub — cheaper at source
    },
}

# Seasonal multipliers by month (1 = base price, <1 = cheaper, >1 = expensive)
SEASONALITY = {
    "cassava_dried": {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.1, 6: 1.15, 7: 1.2, 8: 1.1, 9: 0.85, 10: 0.8, 11: 0.85, 12: 0.95},
    "maize_dried": {1: 1.0, 2: 1.05, 3: 1.15, 4: 1.2, 5: 1.25, 6: 1.2, 7: 1.1, 8: 0.9, 9: 0.8, 10: 0.75, 11: 0.8, 12: 0.9},
    "honey_beans": {1: 1.0, 2: 0.95, 3: 0.9, 4: 1.0, 5: 1.15, 6: 1.3, 7: 1.35, 8: 1.25, 9: 1.1, 10: 0.95, 11: 0.85, 12: 0.9},
    "yam": {1: 1.0, 2: 1.05, 3: 1.15, 4: 1.2, 5: 1.25, 6: 1.3, 7: 1.2, 8: 1.0, 9: 0.9, 10: 0.85, 11: 0.9, 12: 0.95},
    "groundnuts": {1: 1.0, 2: 1.05, 3: 1.1, 4: 1.15, 5: 1.2, 6: 1.15, 7: 0.95, 8: 0.85, 9: 0.8, 10: 0.85, 11: 0.9, 12: 0.95},
    "millet": {1: 1.0, 2: 1.05, 3: 1.15, 4: 1.2, 5: 1.15, 6: 1.0, 7: 0.85, 8: 0.8, 9: 0.8, 10: 0.85, 11: 0.9, 12: 0.95},
    "sorghum": {1: 1.0, 2: 1.05, 3: 1.15, 4: 1.2, 5: 1.15, 6: 1.0, 7: 0.9, 8: 0.85, 9: 0.8, 10: 0.85, 11: 0.9, 12: 0.95},
    "rice": {1: 1.0, 2: 1.05, 3: 1.1, 4: 1.15, 5: 1.1, 6: 0.95, 7: 0.85, 8: 0.8, 9: 0.85, 10: 0.9, 11: 0.95, 12: 1.0},
}


def _seeded_random(date: str, commodity: str, market: str, seed: int = 42) -> float:
    """
    Generate deterministic pseudo-random value between 0 and 1.
    Same inputs always produce same output.
    """
    key = f"{date}:{commodity}:{market}:{seed}".encode()
    hash_obj = hashlib.md5(key)
    hash_int = int(hash_obj.hexdigest(), 16)
    return (hash_int % 1000) / 1000.0


def _get_seasonal_multiplier(commodity: str, date: str) -> float:
    """Get seasonal price multiplier based on commodity and month."""
    date_obj = datetime.fromisoformat(date)
    month = date_obj.month
    return SEASONALITY.get(commodity, {}).get(month, 1.0)


def _calculate_price(
    commodity: str, date: str, market: str, seed: int = 42, weather_modifier: float = 1.0
) -> float:
    """
    Calculate reproducible price with seasonality, regional variance, and weather impact.
    """
    base_price = COMMODITY_BASE_PRICES.get(commodity, 500.0)
    seasonal_mult = _get_seasonal_multiplier(commodity, date)
    regional_mult = MARKETS[market]["regional_multiplier"]

    # Add small variation (±2%) within the date/commodity/market/seed combo
    variation = _seeded_random(date, commodity, market, seed)
    variation_factor = 0.98 + (variation * 0.04)  # 0.98 to 1.02

    price = base_price * seasonal_mult * regional_mult * variation_factor * weather_modifier
    return round(price, 2)


def generate_market_prices(date: str, market_id: str | None = None, seed: int = 42) -> list:
    """
    Generate market prices for a given date and optional market.

    Args:
        date: ISO8601 date string (e.g., "2026-05-08")
        market_id: Optional market filter. If None, returns all markets.
        seed: Seed for reproducibility (fixed globally, learners don't see it)

    Returns:
        List of market price records for the requested date.
    """
    date_obj = datetime.fromisoformat(date)
    recorded_at = date_obj.replace(hour=10, minute=30, second=0, microsecond=0).isoformat() + "Z"

    markets_to_query = [market_id] if market_id else MARKETS.keys()

    results = []
    for market in markets_to_query:
        if market not in MARKETS:
            continue

        market_data = MARKETS[market]

        weather = generate_weather(date, market)
        weather_mod = get_weather_modifier(weather)

        prices = []
        for commodity in sorted(COMMODITY_BASE_PRICES.keys()):
            price = _calculate_price(commodity, date, market, seed, weather_mod)
            prices.append(
                PriceRecord(
                    commodity_id=commodity,
                    commodity_name=_commodity_display_name(commodity),
                    unit="kg",
                    unit_price_ngn=price,
                    recorded_at=recorded_at,
                )
            )

        results.append({
            "date": date,
            "market": {
                "id": market_data["id"],
                "name": market_data["name"],
                "region": market_data["region"],
                "lat": market_data["lat"],
                "lon": market_data["lon"],
            },
            "prices": prices,
        })

    return results


def get_available_dates(days_back: int = 30) -> list[str]:
    """Get list of available dates (last N days)."""
    today = datetime.now().date()
    return [
        (today - timedelta(days=i)).isoformat()
        for i in range(days_back)
    ]


def _commodity_display_name(commodity_id: str) -> str:
    """Convert commodity_id to display name."""
    names = {
        "cassava_dried": "Dried Cassava",
        "maize_dried": "Dried Maize",
        "honey_beans": "Beans (Honey Beans)",
        "yam": "Yam (Dried)",
        "groundnuts": "Groundnuts",
        "millet": "Millet",
        "sorghum": "Sorghum",
        "rice": "Rice",
    }
    return names.get(commodity_id, commodity_id)
