"""
Act 3 — Snapshot load with source-provided rate_date.

The CBN has started including rate_date in every row. The pipeline now
stores both snapshot_date (derived from the filename by the pipeline) and
rate_date (from the source CSV). On weekdays these match. On weekends they
diverge: snapshot_date is Saturday or Sunday, rate_date is the preceding
Friday — because CBN does not publish on weekends.

Run against phase_2 files (which include rate_date):
    python solutions/v3_rate_date_load.py data/cbn/phase_2/cbn_fx_rates_2026-05-24.csv
    python solutions/v3_rate_date_load.py data/cbn/phase_2/cbn_fx_rates_2026-05-25.csv  ← Saturday
    ...

Reset between demos:
    psql -c "DROP TABLE IF EXISTS cbn_fx_rates;"
"""

import csv
import re
import sys
from datetime import date
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
    is_forward_filled BOOLEAN,
    snapshot_date     DATE,
    rate_date         DATE
);
"""

DELETE = "DELETE FROM cbn_fx_rates WHERE snapshot_date = %(snapshot_date)s;"

INSERT = """
INSERT INTO cbn_fx_rates
    (currency_code, currency, buying_rate, central_rate, selling_rate,
     is_forward_filled, snapshot_date, rate_date)
VALUES
    (%(currency_code)s, %(currency)s, %(buying_rate)s, %(central_rate)s,
     %(selling_rate)s, %(is_forward_filled)s, %(snapshot_date)s, %(rate_date)s);
"""


def parse_date(path: Path) -> date:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not m:
        raise ValueError(f"Cannot parse date from filename: {path.name}")
    return date.fromisoformat(m.group(1))


def load(csv_path: Path) -> None:
    snapshot_date = parse_date(csv_path)

    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["is_forward_filled"] = row["is_forward_filled"].lower() == "true"
        row["snapshot_date"] = snapshot_date

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE)
            cur.execute(DELETE, {"snapshot_date": snapshot_date})
            cur.executemany(INSERT, rows)
        conn.commit()
        rate_date = rows[0]["rate_date"] if rows else "n/a"
        print(
            f"Loaded {len(rows)} rows from {csv_path.name} "
            f"(snapshot_date={snapshot_date}, rate_date={rate_date})"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python v3_rate_date_load.py <csv_path>")
    load(Path(sys.argv[1]))
