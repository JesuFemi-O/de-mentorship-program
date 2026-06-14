"""
Demo 1 - Naive Full Load

A full load replaces the entire table every time it runs.
The simplest approach: TRUNCATE, then INSERT everything from the CSV.

Run it once - 13 rows land in the table.
Run it again with the same file - still 13 rows (idempotent within a day).
Run it with Tuesday's file after Monday's - Monday's data is GONE.

That last point is the lesson: naive full load does not preserve history.

Usage:
    python week_1_full_load_ingestion/naive_load.py week_1_full_load_ingestion/data/cbn/cbn_fx_rates_2026-06-04.csv

Reset between runs:
    psql -c "DROP TABLE IF EXISTS cbn_fx_rates;"
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from shared.db import get_connection

# ---------------------------------------------------------------------------
# SQL - fill in the blanks
# ---------------------------------------------------------------------------

# TODO 1: Write the CREATE TABLE statement.
#   Columns:
#     currency_code     TEXT
#     currency          TEXT
#     buying_rate       NUMERIC(12, 4)
#     central_rate      NUMERIC(12, 4)
#     selling_rate      NUMERIC(12, 4)
#     is_forward_filled BOOLEAN
#
#   Use CREATE TABLE IF NOT EXISTS so re-running doesn't fail if the table
#   already exists.
CREATE = """
CREATE TABLE IF NOT EXISTS cbn_fx_rates (
    currency_code TEXT,
    currency TEXT,
    buying_rate NUMERIC(12, 4),
    central_rate NUMERIC(12, 4),
    selling_rate NUMERIC(12, 4),
    is_forward_filled BOOLEAN
)
"""

# TODO 2: Write the TRUNCATE statement.
#   This wipes the whole table before every load - that is what makes it
#   "naive".  A single SQL keyword is enough.
TRUNCATE = """
TRUNCATE TABLE cbn_fx_rates
"""

# TODO 3: Write the INSERT statement.
#   Insert one row using %(column_name)s placeholders for each column.
#   The column names must match the keys in the row dicts you will build
#   from the CSV.
INSERT = """
INSERT INTO cbn_fx_rates
    (currency_code, currency, buying_rate, central_rate, selling_rate, is_forward_filled)
VALUES
    (%(currency_code)s, %(currency)s, %(buying_rate)s, %(central_rate)s,
     %(selling_rate)s, %(is_forward_filled)s);
"""


# ---------------------------------------------------------------------------
# Load function - fill in the blanks
# ---------------------------------------------------------------------------
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


    print(f"Loaded {len(rows)} rows from {csv_path.name}")


# ---------------------------------------------------------------------------
# Entry point - no changes needed below this line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python naive_load.py <path/to/cbn_fx_rates_YYYY-MM-DD.csv>")
    load(Path(sys.argv[1]))
