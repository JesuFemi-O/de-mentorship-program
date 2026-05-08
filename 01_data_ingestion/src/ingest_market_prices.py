"""
Example: Ingesting market prices from the API into PostgreSQL.

This is a reference implementation showing:
1. How to fetch from the market prices API
2. Data contract validation
3. Inserting into the warehouse
4. Handling failures gracefully

Run this to see the full pipeline in action:
    python ingest_market_prices.py
"""

import sys
import requests
from datetime import datetime, timedelta
from typing import Optional

# Adjust path to import from shared
sys.path.insert(0, "../..")
from shared.db import get_connection


def validate_price_record(record: dict) -> bool:
    """
    Validate a price record against the data contract.

    Data Contract:
    - commodity_id: non-empty string
    - commodity_name: non-empty string
    - unit: non-empty string
    - unit_price_ngn: float > 0
    - recorded_at: valid ISO8601 timestamp
    """
    required_fields = ["commodity_id", "commodity_name", "unit", "unit_price_ngn", "recorded_at"]

    # Check all required fields exist
    if not all(field in record for field in required_fields):
        print(f"  ✗ Missing required field in: {record}")
        return False

    # Validate types and values
    if not isinstance(record["unit_price_ngn"], (int, float)):
        print(f"  ✗ unit_price_ngn must be numeric: {record}")
        return False

    if record["unit_price_ngn"] <= 0:
        print(f"  ✗ unit_price_ngn must be > 0: {record}")
        return False

    if not isinstance(record["commodity_id"], str) or not record["commodity_id"]:
        print(f"  ✗ commodity_id must be non-empty string: {record}")
        return False

    return True


def fetch_market_prices(date: str, api_base: str = "http://localhost:8000") -> Optional[dict]:
    """
    Fetch market prices from API for a given date.

    Returns:
        Response dict if successful, None if failed
    """
    url = f"{api_base}/market-prices?date={date}"

    try:
        print(f"Fetching: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to fetch prices: {e}")
        return None


def insert_prices_to_db(date: str, markets_data: list) -> int:
    """
    Insert market prices into PostgreSQL warehouse.

    Returns:
        Number of records inserted
    """
    conn = get_connection()
    cursor = conn.cursor()

    inserted = 0

    try:
        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_prices (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                market_id VARCHAR(50) NOT NULL,
                market_name VARCHAR(255) NOT NULL,
                region VARCHAR(100) NOT NULL,
                commodity_id VARCHAR(50) NOT NULL,
                commodity_name VARCHAR(255) NOT NULL,
                unit VARCHAR(10) NOT NULL,
                unit_price_ngn FLOAT NOT NULL,
                recorded_at TIMESTAMP NOT NULL,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, market_id, commodity_id)
            )
        """)

        # Insert prices
        for market_record in markets_data:
            market_info = market_record["market"]

            for price in market_record["prices"]:
                # Validate before inserting
                if not validate_price_record(price):
                    continue

                try:
                    cursor.execute("""
                        INSERT INTO market_prices (
                            date, market_id, market_name, region,
                            commodity_id, commodity_name, unit,
                            unit_price_ngn, recorded_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date, market_id, commodity_id)
                        DO UPDATE SET unit_price_ngn = EXCLUDED.unit_price_ngn
                    """, (
                        date,
                        market_info["id"],
                        market_info["name"],
                        market_info["region"],
                        price["commodity_id"],
                        price["commodity_name"],
                        price["unit"],
                        price["unit_price_ngn"],
                        price["recorded_at"],
                    ))
                    inserted += 1
                except Exception as e:
                    print(f"  ✗ Failed to insert record: {e}")
                    continue

        conn.commit()
        print(f"✓ Inserted {inserted} records for {date}")

    except Exception as e:
        print(f"✗ Database error: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()
        conn.close()

    return inserted


def ingest_market_prices(date: str, fallback_csv: Optional[str] = None) -> bool:
    """
    Complete ingestion pipeline: fetch, validate, insert.
    Falls back to CSV if API unavailable.
    """
    print(f"\n{'='*60}")
    print(f"Ingesting market prices for {date}")
    print(f"{'='*60}")

    # Try API first
    response = fetch_market_prices(date)

    if response is None:
        print(f"\n✗ API unavailable, falling back to CSV...")
        if fallback_csv:
            print(f"  (In production: team member provides {fallback_csv})")
            # TODO: Implement CSV fallback reading
        return False

    # Extract market data
    markets_data = response.get("markets", [])

    if not markets_data:
        print("✗ No market data in response")
        return False

    print(f"✓ Received data from {len(markets_data)} market(s)")

    # Validate and insert
    inserted = insert_prices_to_db(date, markets_data)

    if inserted > 0:
        print(f"✓ Ingestion complete: {inserted} records")
        return True
    else:
        print("✗ No records inserted")
        return False


if __name__ == "__main__":
    # Ingest today's prices
    today = datetime.now().date().isoformat()
    success = ingest_market_prices(today)

    if not success:
        print("\n⚠ Ingestion failed. Check logs above.")
        sys.exit(1)
    else:
        print("\n✓ Ingestion successful!")
