from market_data import (
    generate_market_prices,
    get_available_dates,
    _calculate_price,
    MARKETS,
    COMMODITY_BASE_PRICES,
)


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------

def test_kano_central_exists():
    assert "kano_central" in MARKETS


def test_kano_is_north_region():
    assert MARKETS["kano_central"]["region"] == "North"


def test_all_five_markets_present():
    expected = {"lagos_lekki", "makurdi_central", "jos_main", "kaduna_central", "kano_central"}
    assert set(MARKETS.keys()) == expected


# ---------------------------------------------------------------------------
# generate_market_prices — structure
# ---------------------------------------------------------------------------

def test_returns_all_markets_when_no_filter():
    results = generate_market_prices("2026-05-08")
    returned_ids = {r["market"]["id"] for r in results}
    assert returned_ids == set(MARKETS.keys())


def test_filter_by_market_returns_one():
    results = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    assert len(results) == 1
    assert results[0]["market"]["id"] == "lagos_lekki"


def test_invalid_market_filter_returns_empty():
    results = generate_market_prices("2026-05-08", market_id="nonexistent_market")
    assert results == []


def test_all_commodities_included_per_market():
    results = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    commodity_ids = {p["commodity_id"] for p in results[0]["prices"]}
    assert commodity_ids == set(COMMODITY_BASE_PRICES.keys())


def test_regional_multiplier_not_in_response():
    results = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    assert "regional_multiplier" not in results[0]["market"]


def test_market_response_has_expected_keys():
    results = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    market = results[0]["market"]
    for key in ("id", "name", "region", "lat", "lon"):
        assert key in market


# ---------------------------------------------------------------------------
# PriceRecord contract
# ---------------------------------------------------------------------------

def test_price_record_has_all_contract_fields():
    results = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    price = results[0]["prices"][0]
    for field in ("commodity_id", "commodity_name", "unit", "unit_price_ngn", "recorded_at"):
        assert field in price


def test_unit_always_kg():
    results = generate_market_prices("2026-05-08")
    for market_record in results:
        for price in market_record["prices"]:
            assert price["unit"] == "kg"


def test_all_prices_positive():
    results = generate_market_prices("2026-05-08")
    for market_record in results:
        for price in market_record["prices"]:
            assert price["unit_price_ngn"] > 0


def test_commodity_id_non_empty_string():
    results = generate_market_prices("2026-05-08", market_id="kano_central")
    for price in results[0]["prices"]:
        assert isinstance(price["commodity_id"], str)
        assert price["commodity_id"] != ""


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_date_same_prices():
    r1 = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    r2 = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    assert r1[0]["prices"] == r2[0]["prices"]


def test_different_dates_different_prices():
    r1 = generate_market_prices("2026-05-01", market_id="lagos_lekki")
    r2 = generate_market_prices("2026-05-08", market_id="lagos_lekki")
    prices1 = [p["unit_price_ngn"] for p in r1[0]["prices"]]
    prices2 = [p["unit_price_ngn"] for p in r2[0]["prices"]]
    assert prices1 != prices2


# ---------------------------------------------------------------------------
# Weather modifier integration
# ---------------------------------------------------------------------------

def test_weather_modifier_raises_price():
    base = _calculate_price("yam", "2026-05-08", "lagos_lekki", weather_modifier=1.0)
    boosted = _calculate_price("yam", "2026-05-08", "lagos_lekki", weather_modifier=1.05)
    assert boosted > base
    assert round(boosted / base, 4) == round(1.05, 4)


def test_weather_modifier_default_is_one():
    price_default = _calculate_price("yam", "2026-05-08", "lagos_lekki")
    price_explicit = _calculate_price("yam", "2026-05-08", "lagos_lekki", weather_modifier=1.0)
    assert price_default == price_explicit


# ---------------------------------------------------------------------------
# Regional pricing
# ---------------------------------------------------------------------------

def test_kano_cheaper_than_lagos_without_weather():
    # With identical weather modifier, Kano's lower regional_multiplier wins
    price_kano = _calculate_price("yam", "2026-05-08", "kano_central", weather_modifier=1.0)
    price_lagos = _calculate_price("yam", "2026-05-08", "lagos_lekki", weather_modifier=1.0)
    assert price_kano < price_lagos


def test_middle_belt_cheaper_than_lagos_without_weather():
    price_makurdi = _calculate_price("maize_dried", "2026-05-08", "makurdi_central", weather_modifier=1.0)
    price_lagos = _calculate_price("maize_dried", "2026-05-08", "lagos_lekki", weather_modifier=1.0)
    assert price_makurdi < price_lagos


# ---------------------------------------------------------------------------
# Available dates
# ---------------------------------------------------------------------------

def test_get_available_dates_returns_thirty():
    assert len(get_available_dates(days_back=30)) == 30


def test_available_dates_most_recent_first():
    dates = get_available_dates(days_back=30)
    assert dates[0] > dates[-1]


def test_available_dates_are_iso8601_strings():
    from datetime import date
    dates = get_available_dates(days_back=5)
    for d in dates:
        date.fromisoformat(d)  # raises if invalid format
