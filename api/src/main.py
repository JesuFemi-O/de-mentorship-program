import hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from market_data import generate_market_prices, get_available_dates, MARKETS
from weather_data import generate_weather

app = FastAPI(title="GreenVault Market Prices API", version="2.0")



class PriceRecord(BaseModel):
    commodity_id: str
    commodity_name: str
    unit: str
    unit_price_ngn: float
    recorded_at: str


class MarketInfo(BaseModel):
    id: str
    name: str
    region: str
    lat: float
    lon: float


class MarketPriceEntry(BaseModel):
    date: str
    market: MarketInfo
    prices: list[PriceRecord]


class ResponseMetadata(BaseModel):
    version: str
    available_dates: list[str]
    available_markets: list[str]


class MarketPricesResponse(BaseModel):
    date: str
    markets: list[MarketPriceEntry]
    metadata: ResponseMetadata


class WeatherRecord(BaseModel):
    date: str
    market_id: str
    region: str
    season: str
    temperature_c: float
    humidity_percent: float
    rainfall_mm: float
    wind_speed_kmh: float
    wind_direction: str
    sunshine_hours: float
    cloud_cover_percent: float
    harmattan_active: bool
    dust_intensity: Optional[str] = None
    visibility_km: Optional[float] = None
    air_quality_index: Optional[int] = None


class WeatherResponse(BaseModel):
    date: str
    weather: list[WeatherRecord]
    metadata: ResponseMetadata


# --- Helpers ---

def _validate_request(date: str, market: str | None) -> list[str]:
    """Validate date format, range, and optional market. Returns the available dates list."""
    try:
        datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use ISO8601 (e.g., 2026-05-08)"
        )

    available = get_available_dates(days_back=30)
    if date not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Date out of range. Available dates: {available[0]} to {available[-1]}"
        )

    if market and market not in MARKETS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid market. Available: {', '.join(MARKETS.keys())}"
        )

    return available


def _is_api_down(date: str) -> bool:
    """
    Deterministically simulate outages - ~20% of dates fail.
    Same date always behaves the same way across all learners.
    """
    key = f"{date}:outage:42".encode()
    return int(hashlib.md5(key).hexdigest(), 16) % 5 == 0


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/market-prices", response_model=MarketPricesResponse)
def market_prices(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    Get market prices for a given date.

    Returns price records for all markets (or a single market if filtered).

    Possible responses:
    - 200: prices returned successfully
    - 400: invalid date format, date out of range, or unknown market ID
    - 503: service temporarily unavailable - the upstream data source could not be reached for this date
    """
    available = _validate_request(date, market)

    if _is_api_down(date):
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. The upstream data source could not be reached for this date."
        )

    market_data = generate_market_prices(date, market_id=market)
    return {
        "date": date,
        "markets": market_data,
        "metadata": {
            "version": "1.0",
            "available_dates": available,
            "available_markets": list(MARKETS.keys()),
        },
    }


@app.get("/weather", response_model=WeatherResponse)
def weather(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    Get weather conditions for a given date.

    Harmattan fields (dust_intensity, visibility_km, air_quality_index) are null
    outside of December-February.

    Possible responses:
    - 200: weather data returned successfully
    - 400: invalid date format, date out of range, or unknown market ID
    - 503: service temporarily unavailable - the upstream data source could not be reached for this date
    """
    available = _validate_request(date, market)

    if _is_api_down(date):
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. The upstream data source could not be reached for this date."
        )

    markets_to_query = [market] if market else list(MARKETS.keys())
    weather_records = [generate_weather(date, m) for m in markets_to_query]
    return {
        "date": date,
        "weather": weather_records,
        "metadata": {
            "version": "1.0",
            "available_dates": available,
            "available_markets": list(MARKETS.keys()),
        },
    }


@app.get("/v2/market-prices", response_model=MarketPricesResponse)
def market_prices_v2(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    Get market prices for a given date (v2).

    Same contract as /market-prices. Returns price records for all markets
    (or a single market if filtered).

    Possible responses:
    - 200: prices returned successfully
    - 400: invalid date format, date out of range, or unknown market ID
    """
    available = _validate_request(date, market)
    market_data = generate_market_prices(date, market_id=market)
    return {
        "date": date,
        "markets": market_data,
        "metadata": {
            "version": "2.0",
            "available_dates": available,
            "available_markets": list(MARKETS.keys()),
        },
    }


@app.get("/v2/weather", response_model=WeatherResponse)
def weather_v2(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    Get weather conditions for a given date (v2).

    Same contract as /weather. Harmattan fields (dust_intensity, visibility_km,
    air_quality_index) are null outside of December-February.

    Possible responses:
    - 200: weather data returned successfully
    - 400: invalid date format, date out of range, or unknown market ID
    """
    available = _validate_request(date, market)
    markets_to_query = [market] if market else list(MARKETS.keys())
    weather_records = [generate_weather(date, m) for m in markets_to_query]
    return {
        "date": date,
        "weather": weather_records,
        "metadata": {
            "version": "2.0",
            "available_dates": available,
            "available_markets": list(MARKETS.keys()),
        },
    }
