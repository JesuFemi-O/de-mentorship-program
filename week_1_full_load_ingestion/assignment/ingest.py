"""
Week 1 Assignment - Full-Load Ingestion

Goal: write a pipeline that reads a CBN FX rate CSV and loads it into a local
DuckDB table using the full-load pattern.

A full load replaces the entire table on every run.
Run it twice with the same file and you still see 13 rows - that is idempotent.
Run it for Monday then run it for Tuesday - Monday's data is gone.
That loss of history is the pattern's defining tradeoff, and the point of this week.

The source: a dated CBN FX rate CSV, e.g.
    week_1_full_load_ingestion/data/cbn/cbn_fx_rates_2026-06-04.csv

The target: a local DuckDB file - cbn_fx.duckdb - in the current directory.
DuckDB needs no server. Open it with:
    conn = duckdb.connect("cbn_fx.duckdb")

Usage (run from the repo root):
    python week_1_full_load_ingestion/assignment/ingest.py \\
        week_1_full_load_ingestion/data/cbn/cbn_fx_rates_2026-06-04.csv

Verify:
    python -c "
    import duckdb
    conn = duckdb.connect('cbn_fx.duckdb')
    print(conn.execute('SELECT * FROM cbn_fx_rates').fetchdf())
    "

Reset between attempts:
    rm -f cbn_fx.duckdb
"""

import csv
import sys
from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# SQL - fill in the blanks
# ---------------------------------------------------------------------------

# TODO 1: Write the CREATE TABLE IF NOT EXISTS statement.
#   Columns:
#     currency_code     VARCHAR
#     currency          VARCHAR
#     buying_rate       DOUBLE
#     central_rate      DOUBLE
#     selling_rate      DOUBLE
#     is_forward_filled BOOLEAN
CREATE = """
-- TODO 1: write the CREATE TABLE IF NOT EXISTS statement here
"""

# TODO 2: Write the TRUNCATE statement.
#   This wipes the whole table before every load - that is what makes it
#   a full load.  A single SQL keyword is enough.
TRUNCATE = """
-- TODO 2: write the TRUNCATE statement here
"""

# TODO 3: Write the INSERT statement.
#   Insert one row using ? as the placeholder for each value.
#   The order of ? must match the order you pass values in load().
INSERT = """
-- TODO 3: write the INSERT statement here
"""


# ---------------------------------------------------------------------------
# Load function - fill in the blanks
# ---------------------------------------------------------------------------


def load(csv_path: Path) -> None:
    # TODO 4: Open csv_path and read it into a list of dicts.
    #   Use csv.DictReader - it turns each row into a dict whose keys come
    #   from the CSV header.
    rows: list[dict] = []  # replace this

    # TODO 5: The CSV stores is_forward_filled as the string "True" or "False".
    #   Convert it to a Python bool for every row before inserting.
    #   Hint: row["is_forward_filled"].lower() == "true"

    # TODO 6: Convert rows to a list of tuples in column order:
    #     (currency_code, currency, buying_rate, central_rate,
    #      selling_rate, is_forward_filled)
    #   Then open a DuckDB connection, run CREATE, TRUNCATE, and INSERT all
    #   rows, then close the connection.
    #
    #   Pattern:
    #     conn = duckdb.connect("cbn_fx.duckdb")

    print(f"Loaded {len(rows)} rows from {csv_path.name}")


# ---------------------------------------------------------------------------
# Entry point - no changes needed below this line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python ingest.py <path/to/cbn_fx_rates_YYYY-MM-DD.csv>")
    load(Path(sys.argv[1]))
