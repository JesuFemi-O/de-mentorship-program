"""
Demo 2 — Snapshot full load.

Same source data as v1, but the pipeline stamps snapshot_date on every row
by parsing the date from the filename. Rows for a given snapshot_date are
deleted before reinserting, so re-running the same file is idempotent and
running a new file accumulates history rather than wiping it.

Usage (run once per file to accumulate the week):
    python solutions/v2_snapshot_load.py data/cbn/phase_1/cbn_fx_rates_2026-05-19.csv
    python solutions/v2_snapshot_load.py data/cbn/phase_1/cbn_fx_rates_2026-05-20.csv
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
    snapshot_date     DATE
);
"""

DELETE = "DELETE FROM cbn_fx_rates WHERE snapshot_date = %(snapshot_date)s;"

INSERT = """
INSERT INTO cbn_fx_rates
    (currency_code, currency, buying_rate, central_rate, selling_rate,
     is_forward_filled, snapshot_date)
VALUES
    (%(currency_code)s, %(currency)s, %(buying_rate)s, %(central_rate)s,
     %(selling_rate)s, %(is_forward_filled)s, %(snapshot_date)s);
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
        print(f"Loaded {len(rows)} rows from {csv_path.name} (snapshot_date={snapshot_date})")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python v2_snapshot_load.py <csv_path>")
    load(Path(sys.argv[1]))
