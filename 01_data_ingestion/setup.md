# Chapter 01: Data Ingestion — Setup

## Prerequisites

This chapter requires:
- PostgreSQL running (see Local Stack below)
- Python 3.11+ with dependencies installed
- Basic familiarity with HTTP APIs

---

## Local Stack

This chapter uses the following services:

| Service    | Purpose          | Port |
|------------|------------------|------|
| PostgreSQL | Primary database | 5432 |

### Starting the stack

```bash
cp ../.env.example ../.env   # configure credentials if needed
cd ../infrastructure
docker compose up -d
```

### Stopping the stack

```bash
cd ../infrastructure
docker compose down      # stop containers
docker compose down -v   # stop and remove volumes (full reset)
```

> Volume data is mounted to `infrastructure/volumes/` — delete that folder for a clean slate.

---

## Starting the Market Prices API

The market prices API serves daily commodity prices from Nigerian agricultural markets.

### Run the API server

From the chapter root directory:

```bash
cd src
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### Test the API

**Get today's prices (all markets):**
```bash
curl "http://localhost:8000/market-prices?date=2026-05-08"
```

**Get prices for a specific market:**
```bash
curl "http://localhost:8000/market-prices?date=2026-05-08&market=lagos_lekki"
```

**Get historical prices:**
```bash
curl "http://localhost:8000/market-prices?date=2026-05-01"
```

**Get today's weather (all markets):**
```bash
curl "http://localhost:8000/weather?date=2026-05-08"
```

**Get weather for a specific market:**
```bash
curl "http://localhost:8000/weather?date=2026-05-08&market=kano_central"
```

> Notice that `dust_intensity`, `visibility_km`, and `air_quality_index` are `null` outside of the Harmattan period (December–February). Try a date in January to see them populated.

### v2 endpoints (intermittent failures)

The v2 endpoints have the same contract as v1 but fail with `503` on ~20% of dates. Failures are deterministic — the same date always fails or succeeds, so you can reliably reproduce your fallback logic.

```bash
# This date may return 503 — check if yours does
curl "http://localhost:8000/v2/market-prices?date=2026-05-08"

# Same outage applies to weather on the same date
curl "http://localhost:8000/v2/weather?date=2026-05-08"
```

**API documentation (interactive):**
Open http://localhost:8000/docs in your browser for Swagger UI.

---

## Fallback Data

When the API is unavailable, you can use fallback CSV data collected by our field team.

### Generate fallback data

```bash
cd src
python generate_fallback_data.py
```

This creates two files:

- `fallback_market_prices.csv` — 30 days of market price data
- `fallback_weather.csv` — 30 days of weather data (includes `null` Harmattan fields for non-Harmattan periods)

---

## Database Tools

For exploring and querying your PostgreSQL warehouse:

- [PostgreSQL VS Code extension](https://marketplace.visualstudio.com/items?itemName=ms-ossdata.vscode-pgsql) — lightweight, integrated
- [DBeaver Community Edition](https://dbeaver.io/download/) — full-featured, works with many databases
- [pgAdmin](https://www.pgadmin.org/) — web-based interface

---

## Next Steps

1. ✅ Start PostgreSQL (`docker compose up -d`)
2. ✅ Run the API server (`uvicorn main:app --reload`)
3. ✅ Explore the API in Swagger UI
4. → Build your ingestion script in `src/ingest_market_prices.py`

See [README.md](README.md) for learning objectives and the data contract.
