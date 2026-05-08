import hashlib
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query

from market_data import generate_market_prices, get_available_dates, MARKETS
from weather_data import generate_weather

app = FastAPI(title="Market Prices API", version="2.0")


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
    Deterministically simulate outages — ~20% of dates fail.
    Same date always behaves the same way across all learners.
    """
    key = f"{date}:outage:42".encode()
    return int(hashlib.md5(key).hexdigest(), 16) % 5 == 0


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/market-prices")
def market_prices(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    v1: Get market prices for a given date. Always succeeds.

    Use this while building your ingestion pipeline before adding fallback logic.
    Switch to /v2/market-prices when you're ready to handle failures.
    """
    available = _validate_request(date, market)
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


@app.get("/weather")
def weather(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    v1: Get weather conditions for a given date. Always succeeds.

    Harmattan fields (dust_intensity, visibility_km, air_quality_index) are null
    outside of December–February.
    """
    available = _validate_request(date, market)
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


@app.get("/v2/market-prices")
def market_prices_v2(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    v2: Same contract as /market-prices but with intermittent outages (~20% of dates).

    When down, returns 503. Your pipeline must detect this and fall back to
    fallback_market_prices.csv. Outages are deterministic — the same date always
    fails or succeeds, so you can reliably reproduce and test your fallback logic.
    Outages are correlated with /v2/weather: if one is down, both are down.
    """
    available = _validate_request(date, market)

    if _is_api_down(date):
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Use your fallback data source."
        )

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


@app.get("/v2/weather")
def weather_v2(
    date: str = Query(..., description="ISO8601 date (e.g., 2026-05-08)"),
    market: str | None = Query(None, description="Optional market ID filter"),
):
    """
    v2: Same contract as /weather but with intermittent outages (~20% of dates).

    Outages are correlated with /v2/market-prices — if one is down on a given
    date, both are down. Fall back to fallback_weather.csv when 503 is returned.
    """
    available = _validate_request(date, market)

    if _is_api_down(date):
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Use your fallback data source."
        )

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
