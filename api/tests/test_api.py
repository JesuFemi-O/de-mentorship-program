import pytest
from fastapi.testclient import TestClient

from main import app, _is_api_down
from market_data import get_available_dates, MARKETS

client = TestClient(app)


def _split_dates():
    """Return one date that triggers a v2 outage and one that doesn't."""
    dates = get_available_dates(days_back=30)
    failing = next((d for d in dates if _is_api_down(d)), None)
    passing = next((d for d in dates if not _is_api_down(d)), None)
    return failing, passing


FAILING_DATE, PASSING_DATE = _split_dates()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_returns_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# v1 /market-prices — always succeeds
# ---------------------------------------------------------------------------

def test_v1_prices_valid_date():
    r = client.get(f"/market-prices?date={PASSING_DATE}")
    assert r.status_code == 200


def test_v1_prices_response_shape():
    r = client.get(f"/market-prices?date={PASSING_DATE}")
    body = r.json()
    assert "date" in body
    assert "markets" in body
    assert "metadata" in body
    assert body["metadata"]["version"] == "1.0"


def test_v1_prices_all_markets_returned():
    r = client.get(f"/market-prices?date={PASSING_DATE}")
    returned_ids = {m["market"]["id"] for m in r.json()["markets"]}
    assert returned_ids == set(MARKETS.keys())


def test_v1_prices_filter_by_market():
    r = client.get(f"/market-prices?date={PASSING_DATE}&market=lagos_lekki")
    assert r.status_code == 200
    assert len(r.json()["markets"]) == 1


def test_v1_prices_invalid_date_format():
    r = client.get("/market-prices?date=not-a-date")
    assert r.status_code == 400


def test_v1_prices_date_out_of_range():
    r = client.get("/market-prices?date=2020-01-01")
    assert r.status_code == 400


def test_v1_prices_invalid_market():
    r = client.get(f"/market-prices?date={PASSING_DATE}&market=nowhere")
    assert r.status_code == 400


def test_v1_never_returns_503():
    """v1 is the stable endpoint — it must succeed even on dates that v2 fails."""
    if FAILING_DATE is None:
        pytest.skip("No failing date found in 30-day window")
    r = client.get(f"/market-prices?date={FAILING_DATE}")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# v1 /weather — always succeeds
# ---------------------------------------------------------------------------

def test_v1_weather_valid_date():
    r = client.get(f"/weather?date={PASSING_DATE}")
    assert r.status_code == 200


def test_v1_weather_response_shape():
    r = client.get(f"/weather?date={PASSING_DATE}")
    body = r.json()
    assert "weather" in body
    assert body["metadata"]["version"] == "1.0"


def test_v1_weather_all_markets_returned():
    r = client.get(f"/weather?date={PASSING_DATE}")
    returned_ids = {w["market_id"] for w in r.json()["weather"]}
    assert returned_ids == set(MARKETS.keys())


def test_v1_weather_filter_by_market():
    r = client.get(f"/weather?date={PASSING_DATE}&market=kano_central")
    assert r.status_code == 200
    assert len(r.json()["weather"]) == 1


def test_v1_weather_invalid_market():
    r = client.get(f"/weather?date={PASSING_DATE}&market=nowhere")
    assert r.status_code == 400


def test_v1_weather_never_returns_503():
    if FAILING_DATE is None:
        pytest.skip("No failing date found in 30-day window")
    r = client.get(f"/weather?date={FAILING_DATE}")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# v2 /v2/market-prices — intermittent failures
# ---------------------------------------------------------------------------

def test_v2_prices_succeeds_on_passing_date():
    r = client.get(f"/v2/market-prices?date={PASSING_DATE}")
    assert r.status_code == 200


def test_v2_prices_version_in_metadata():
    r = client.get(f"/v2/market-prices?date={PASSING_DATE}")
    assert r.json()["metadata"]["version"] == "2.0"


def test_v2_prices_fails_on_failing_date():
    if FAILING_DATE is None:
        pytest.skip("No failing date found in 30-day window")
    r = client.get(f"/v2/market-prices?date={FAILING_DATE}")
    assert r.status_code == 503


def test_v2_prices_same_contract_as_v1():
    """When v2 succeeds the response shape and prices must match v1."""
    v1 = client.get(f"/market-prices?date={PASSING_DATE}").json()
    v2 = client.get(f"/v2/market-prices?date={PASSING_DATE}").json()
    assert v1["markets"] == v2["markets"]


def test_v2_prices_invalid_date_still_400():
    r = client.get("/v2/market-prices?date=bad-date")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# v2 /v2/weather — intermittent failures
# ---------------------------------------------------------------------------

def test_v2_weather_succeeds_on_passing_date():
    r = client.get(f"/v2/weather?date={PASSING_DATE}")
    assert r.status_code == 200


def test_v2_weather_version_in_metadata():
    r = client.get(f"/v2/weather?date={PASSING_DATE}")
    assert r.json()["metadata"]["version"] == "2.0"


def test_v2_weather_fails_on_failing_date():
    if FAILING_DATE is None:
        pytest.skip("No failing date found in 30-day window")
    r = client.get(f"/v2/weather?date={FAILING_DATE}")
    assert r.status_code == 503


def test_v2_weather_same_contract_as_v1():
    v1 = client.get(f"/weather?date={PASSING_DATE}").json()
    v2 = client.get(f"/v2/weather?date={PASSING_DATE}").json()
    assert v1["weather"] == v2["weather"]


# ---------------------------------------------------------------------------
# Correlated failures
# ---------------------------------------------------------------------------

def test_v2_outages_correlated_market_prices_and_weather():
    """If market-prices is down, weather must also be down on the same date."""
    if FAILING_DATE is None:
        pytest.skip("No failing date found in 30-day window")
    r_prices = client.get(f"/v2/market-prices?date={FAILING_DATE}")
    r_weather = client.get(f"/v2/weather?date={FAILING_DATE}")
    assert r_prices.status_code == r_weather.status_code == 503


def test_v2_passing_dates_both_succeed():
    r_prices = client.get(f"/v2/market-prices?date={PASSING_DATE}")
    r_weather = client.get(f"/v2/weather?date={PASSING_DATE}")
    assert r_prices.status_code == r_weather.status_code == 200


def test_v2_outage_rate_roughly_twenty_percent():
    """Roughly 1 in 5 dates should fail — validates the seeding logic."""
    dates = get_available_dates(days_back=30)
    failing_count = sum(1 for d in dates if _is_api_down(d))
    # Allow some statistical variance: expect between 4 and 9 failures in 30 dates
    assert 4 <= failing_count <= 9
