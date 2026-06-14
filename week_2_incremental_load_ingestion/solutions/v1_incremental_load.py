"""
Demo 1 solution - CBN incremental load via time partition.

Handles both a directory (backfill) and a single file (daily run).

Usage:
    python week_2_incremental_load_ingestion/solutions/v1_incremental_load.py \\
        week_2_incremental_load_ingestion/data/cbn/history/

    python week_2_incremental_load_ingestion/solutions/v1_incremental_load.py \\
        week_2_incremental_load_ingestion/data/cbn/recent/cbn_fx_rates_2026-06-09.csv

Reset:
    psql -c "DROP TABLE IF EXISTS cbn_fx_rates_partitioned;"
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from shared.db import get_connection

CREATE = """
CREATE TABLE IF NOT EXISTS cbn_fx_rates_partitioned (
    rate_date         DATE,
    currency_code     TEXT,
    currency          TEXT,
    buying_rate       NUMERIC(12, 4),
    central_rate      NUMERIC(12, 4),
    selling_rate      NUMERIC(12, 4),
    is_forward_filled BOOLEAN
);
"""

CHECK = "SELECT COUNT(*) FROM cbn_fx_rates_partitioned WHERE rate_date = %(rate_date)s;"

INSERT = """
INSERT INTO cbn_fx_rates_partitioned
    (rate_date, currency_code, currency, buying_rate, central_rate,
     selling_rate, is_forward_filled)
VALUES
    (%(rate_date)s, %(currency_code)s, %(currency)s, %(buying_rate)s,
     %(central_rate)s, %(selling_rate)s, %(is_forward_filled)s);
"""


def load_file(csv_path: Path, cur) -> str:
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["is_forward_filled"] = row["is_forward_filled"].lower() == "true"
    if not rows:
        return f"{csv_path.name}  (empty, skipped)"
    rate_date = rows[0]["rate_date"]
    cur.execute(CHECK, {"rate_date": rate_date})
    (count,) = cur.fetchone()
    if count > 0:
        return f"{rate_date}  already loaded ({count} rows) - skipped"
    cur.executemany(INSERT, rows)
    return f"{rate_date}  {len(rows)} rows inserted"


def main(target: Path) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE)
            if target.is_dir():
                files = sorted(target.glob("cbn_fx_rates_*.csv"))
                print(f"Loading {len(files)} files from {target}/")
                for f in files:
                    print(f"  {load_file(f, cur)}")
            else:
                print(load_file(target, cur))
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python v1_incremental_load.py <csv_file_or_directory>")
    main(Path(sys.argv[1]))
