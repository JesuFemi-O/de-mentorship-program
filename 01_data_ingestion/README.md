# Chapter 01: Data Ingestion

> **Ready to dive in?** See [setup.md](setup.md) for infrastructure setup.

## Learning Objectives

In this chapter, you'll learn how to:

1. **Fetch data from an external API** — Market prices are published by agricultural organizations, not controlled by us
2. **Validate against a data contract** — Ensure incoming data matches expected schema and constraints
3. **Handle ingestion failures** — API outages happen; we have fallback data sources (our field team)
4. **Insert into a warehouse** — Persist validated data for downstream use
5. **Reproduce bugs reliably** — Same seed = same data every time, across all learners
6. **Handle nullable fields** — A second source (weather) shares the same date/market keys but has fields that only appear under certain conditions

## API Versions

| Version | Endpoints                          | Behaviour                                                           |
|---------|------------------------------------|---------------------------------------------------------------------|
| v1      | `/market-prices`, `/weather`       | Always succeeds — use while building your pipeline                  |
| v2      | `/v2/market-prices`, `/v2/weather` | ~20% of dates return `503` — use when practising fallback handling  |

Both versions share the same data contract. v2 outages are deterministic (same date always fails) and correlated (if market-prices is down on a date, weather is too).

## The Scenario

Agricultural markets in Nigeria publish daily commodity prices. Our farmer payment hub needs these prices to calculate fair compensation based on market rates.

**The Challenge:**
- Market prices come from an external API (unreliable)
- Prices vary by commodity, region, and season — and by weather conditions on the day
- We need historical data for 30 days
- When the API is down, we have field staff collecting prices via phone/SMS

**What You'll Build:**
A data ingestion pipeline that fetches market prices and loads them into PostgreSQL, with fallback to CSV when the API is unavailable.

The API also exposes a `/weather` endpoint. Weather conditions directly affect the prices you ingest: heavy rainfall disrupts road transport to market (prices rise), and Harmattan dust in the dry season slows logistics (prices rise further). Weather is a second data source you can ingest alongside prices.

## Data Contract

All market prices must conform to this contract:

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `commodity_id` | string | ✓ | Non-empty, predefined values |
| `commodity_name` | string | ✓ | Non-empty |
| `unit` | string | ✓ | Always "kg" in v1 |
| `unit_price_ngn` | float | ✓ | Must be > 0 |
| `recorded_at` | ISO8601 | ✓ | Valid timestamp |

### Allowed Commodities

- `cassava_dried`, `maize_dried`, `beans`, `yam`, `groundnuts`, `millet`, `sorghum`, `rice`

### Allowed Markets

- `lagos_lekki` (Lagos)
- `makurdi_central` (Middle Belt)
- `jos_main` (Middle Belt)
- `kaduna_central` (Middle Belt)
- `kano_central` (North)

## Weather Data Contract

The `/weather` endpoint returns one record per market. Most fields are always present. The three Harmattan fields are **nullable** — they are `null` outside of the Harmattan period (December–February) and populated when `harmattan_active` is `true`.

| Field | Type | Nullable | Constraints |
|-------|------|----------|-------------|
| `date` | string | No | ISO8601 date |
| `market_id` | string | No | Non-empty, predefined values |
| `region` | string | No | Non-empty |
| `season` | string | No | `"rainy"` or `"dry"` |
| `temperature_c` | float | No | > 0 |
| `humidity_percent` | float | No | 0–100 |
| `rainfall_mm` | float | No | ≥ 0 |
| `wind_speed_kmh` | float | No | ≥ 0 |
| `wind_direction` | string | No | Non-empty |
| `sunshine_hours` | float | No | ≥ 0 |
| `cloud_cover_percent` | float | No | 0–100 |
| `harmattan_active` | bool | No | |
| `dust_intensity` | string or null | Yes | `"light"`, `"moderate"`, or `"heavy"` when present |
| `visibility_km` | float or null | Yes | > 0 when present |
| `air_quality_index` | integer or null | Yes | > 0 when present |

> The three nullable fields are only populated when `harmattan_active` is `true`. Your validation logic must handle both cases.

## Key Concepts

### Seasonality

Crop prices vary by season based on supply. This endpoint models realistic seasonality:
- **Harvest season:** Prices drop (high supply)
- **Off-season:** Prices rise (low supply)
- **Dried crops:** Can be stored, affecting year-round availability

### Regional Variance

Same commodity, different prices across regions (transport, storage, local demand).

### Weather Impact on Prices

Weather conditions affect commodity prices on the day they are recorded:

- **Heavy rainfall (> 50mm):** Roads flood, trucks can't reach markets — prices rise ~5%
- **Moderate rainfall (25–50mm):** Partial disruption — prices rise ~2%
- **Harmattan (December–February):** Dust reduces visibility and slows logistics
  - North (`kano_central`): heavy dust → prices rise ~6%
  - Middle Belt: moderate dust → prices rise ~3%
  - South Coastal (`lagos_lekki`): light dust → prices rise ~1%

Because weather is deterministically generated from the same seed, price changes are reproducible — you will always see the same price for the same date and market.

### Seeding & Reproducibility

To ensure all learners experience identical data:

- Prices and weather are both deterministically generated from date + market (+ commodity for prices)
- Seeding is automatic — you don't need to specify it
- Same date always produces same prices and weather across learners
