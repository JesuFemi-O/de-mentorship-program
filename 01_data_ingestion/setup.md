# Chapter 01: Data Ingestion - Setup

## Prerequisites

- Docker and Docker Compose
- Python 3.11+

---

## Local Stack

Start all services from the `infrastructure/` directory:

```bash
cp ../.env.example ../.env
cd ../infrastructure
docker compose up -d
```

| Service    | Port | Purpose          |
|------------|------|------------------|
| PostgreSQL | 5432 | Warehouse        |
| API        | 8000 | Market prices    |

**Stop the stack:**
```bash
docker compose down       # stop containers
docker compose down -v    # stop and wipe volumes (full reset)
```

> Volume data is mounted to `infrastructure/volumes/` - delete that folder for a clean slate.

---

## The API

Once the stack is running, the API is available at `http://localhost:8000`.

Interactive docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**

Explore the available endpoints and their request/response shapes there before writing any code.

---

## Fallback Data

When the API is unavailable for a date, field agents submit prices as CSV. To generate the fallback files locally:

```bash
cd api/src
python generate_fallback_data.py
```

This creates:

- `fallback_market_prices.csv`
- `fallback_weather.csv`

---

## Database Tools

For exploring your PostgreSQL warehouse:

- [PostgreSQL VS Code extension](https://marketplace.visualstudio.com/items?itemName=ms-ossdata.vscode-pgsql) - lightweight, integrated
- [DBeaver Community Edition](https://dbeaver.io/download/) - full-featured, works with many databases
- [pgAdmin](https://www.pgadmin.org/) - web-based interface

---

See [README.md](README.md) for context, the data contract, and what you are building.
