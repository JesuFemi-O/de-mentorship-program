"""
Demo 1 - Naive full load.

Truncates the target table and reloads from a single CSV file.
Run it twice for the same file: same result (idempotent).
Run it for Tuesday after Monday: Monday's data is gone.

Usage:
    python week_1_full_load_ingestion/solutions/v1_naive_load.py week_1_full_load_ingestion/data/cbn/cbn_fx_rates_2026-05-19.csv

Reset between demos:
    psql -c "DROP TABLE IF EXISTS cbn_fx_rates;"
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from shared.db import get_connection

CREATE = """
CREATE TABLE IF NOT EXISTS cbn_fx_rates (
    currency_code     TEXT,
    currency          TEXT,
    buying_rate       NUMERIC(12, 4),
    central_rate      NUMERIC(12, 4),
    selling_rate      NUMERIC(12, 4),
    is_forward_filled BOOLEAN
);
"""

TRUNCATE = "TRUNCATE TABLE cbn_fx_rates;"

INSERT = """
INSERT INTO cbn_fx_rates
    (currency_code, currency, buying_rate, central_rate, selling_rate, is_forward_filled)
VALUES
    (%(currency_code)s, %(currency)s, %(buying_rate)s, %(central_rate)s,
     %(selling_rate)s, %(is_forward_filled)s);
"""


def load(csv_path: Path) -> None:
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["is_forward_filled"] = row["is_forward_filled"].lower() == "true"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE)
            cur.execute(TRUNCATE)
            cur.executemany(INSERT, rows)
        conn.commit()
        print(f"Loaded {len(rows)} rows from {csv_path.name}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python v1_naive_load.py <csv_path>")
    load(Path(sys.argv[1]))
