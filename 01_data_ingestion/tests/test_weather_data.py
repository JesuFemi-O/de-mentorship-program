from weather_data import generate_weather, get_weather_modifier, WeatherRecord, MARKET_REGIONS


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_inputs_always_same_output():
    w1 = generate_weather("2026-05-08", "lagos_lekki")
    w2 = generate_weather("2026-05-08", "lagos_lekki")
    assert w1 == w2


def test_different_dates_produce_different_weather():
    w1 = generate_weather("2026-05-01", "lagos_lekki")
    w2 = generate_weather("2026-05-08", "lagos_lekki")
    assert w1 != w2


def test_different_markets_produce_different_weather():
    w1 = generate_weather("2026-05-08", "lagos_lekki")
    w2 = generate_weather("2026-05-08", "kano_central")
    assert w1 != w2


# ---------------------------------------------------------------------------
# Schema — all fields always present
# ---------------------------------------------------------------------------

def test_all_fields_present():
    weather = generate_weather("2026-05-08", "lagos_lekki")
    required = [
        "date", "market_id", "region", "season",
        "temperature_c", "humidity_percent", "rainfall_mm",
        "wind_speed_kmh", "wind_direction", "sunshine_hours",
        "cloud_cover_percent", "harmattan_active",
        "dust_intensity", "visibility_km", "air_quality_index",
    ]
    for field in required:
        assert field in weather, f"Missing field: {field}"


def test_market_id_and_date_echo_back():
    weather = generate_weather("2026-05-08", "kano_central")
    assert weather["date"] == "2026-05-08"
    assert weather["market_id"] == "kano_central"


# ---------------------------------------------------------------------------
# Season assignment
# ---------------------------------------------------------------------------

def test_lagos_may_is_rainy():
    assert generate_weather("2026-05-08", "lagos_lekki")["season"] == "rainy"


def test_lagos_january_is_dry():
    assert generate_weather("2026-01-15", "lagos_lekki")["season"] == "dry"


def test_kano_may_is_rainy():
    assert generate_weather("2026-05-15", "kano_central")["season"] == "rainy"


def test_kano_october_is_dry():
    # October = dry season in the North
    assert generate_weather("2026-10-01", "kano_central")["season"] == "dry"


def test_middle_belt_march_is_dry():
    # March = dry season in Middle Belt (dry: Nov-Mar)
    assert generate_weather("2026-03-10", "makurdi_central")["season"] == "dry"


def test_middle_belt_june_is_rainy():
    assert generate_weather("2026-06-10", "makurdi_central")["season"] == "rainy"


# ---------------------------------------------------------------------------
# Harmattan — null outside period, populated inside
# ---------------------------------------------------------------------------

def test_harmattan_null_in_rainy_season():
    weather = generate_weather("2026-05-08", "lagos_lekki")
    assert weather["harmattan_active"] is False
    assert weather["dust_intensity"] is None
    assert weather["visibility_km"] is None
    assert weather["air_quality_index"] is None


def test_harmattan_active_kano_january():
    weather = generate_weather("2026-01-15", "kano_central")
    assert weather["harmattan_active"] is True
    assert weather["dust_intensity"] == "heavy"
    assert weather["visibility_km"] is not None
    assert weather["air_quality_index"] is not None


def test_harmattan_active_middle_belt_january():
    weather = generate_weather("2026-01-15", "makurdi_central")
    assert weather["harmattan_active"] is True
    assert weather["dust_intensity"] == "moderate"


def test_harmattan_active_lagos_january():
    weather = generate_weather("2026-01-15", "lagos_lekki")
    assert weather["harmattan_active"] is True
    assert weather["dust_intensity"] == "light"


def test_harmattan_null_in_october_lagos():
    # October = rainy season in Lagos, so no Harmattan
    weather = generate_weather("2026-10-01", "lagos_lekki")
    assert weather["harmattan_active"] is False
    assert weather["dust_intensity"] is None


# ---------------------------------------------------------------------------
# Value ranges
# ---------------------------------------------------------------------------

def test_humidity_in_range():
    weather = generate_weather("2026-05-08", "lagos_lekki")
    assert 0 <= weather["humidity_percent"] <= 100


def test_temperature_positive():
    weather = generate_weather("2026-05-08", "kano_central")
    assert weather["temperature_c"] > 0


def test_rainfall_non_negative():
    for market in MARKET_REGIONS:
        w = generate_weather("2026-05-08", market)
        assert w["rainfall_mm"] >= 0


def test_cloud_cover_in_range():
    weather = generate_weather("2026-07-01", "jos_main")
    assert 0 <= weather["cloud_cover_percent"] <= 100


def test_all_markets_generate_without_error():
    for market_id in MARKET_REGIONS:
        weather = generate_weather("2026-05-08", market_id)
        assert weather["market_id"] == market_id


# ---------------------------------------------------------------------------
# Weather modifier
# ---------------------------------------------------------------------------

def _clear_day(market_id: str = "lagos_lekki") -> WeatherRecord:
    return {
        "date": "2026-05-08", "market_id": market_id, "region": "South Coastal",
        "season": "rainy", "temperature_c": 27.0, "humidity_percent": 80.0,
        "rainfall_mm": 0.0, "wind_speed_kmh": 15.0, "wind_direction": "SW",
        "sunshine_hours": 4.5, "cloud_cover_percent": 70.0,
        "harmattan_active": False, "dust_intensity": None,
        "visibility_km": None, "air_quality_index": None,
    }


def test_modifier_clear_day_is_one():
    assert get_weather_modifier(_clear_day()) == 1.0


def test_modifier_heavy_rain_is_five_percent():
    weather = _clear_day()
    weather["rainfall_mm"] = 60.0
    assert get_weather_modifier(weather) == round(1.05, 4)


def test_modifier_moderate_rain_is_two_percent():
    weather = _clear_day()
    weather["rainfall_mm"] = 30.0
    assert get_weather_modifier(weather) == round(1.02, 4)


def test_modifier_light_rain_no_change():
    weather = _clear_day()
    weather["rainfall_mm"] = 10.0  # below 25mm threshold
    assert get_weather_modifier(weather) == 1.0


def test_modifier_heavy_harmattan():
    weather = _clear_day()
    weather["harmattan_active"] = True
    weather["dust_intensity"] = "heavy"
    assert get_weather_modifier(weather) == round(1.06, 4)


def test_modifier_moderate_harmattan():
    weather = _clear_day()
    weather["harmattan_active"] = True
    weather["dust_intensity"] = "moderate"
    assert get_weather_modifier(weather) == round(1.03, 4)


def test_modifier_heavy_rain_plus_harmattan_compounds():
    weather = _clear_day()
    weather["rainfall_mm"] = 60.0
    weather["harmattan_active"] = True
    weather["dust_intensity"] = "heavy"
    modifier = get_weather_modifier(weather)
    assert modifier == round(1.05 * 1.06, 4)
    assert modifier > 1.05  # compounding, not additive
