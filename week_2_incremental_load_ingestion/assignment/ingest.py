"""
Week 2 Assignment - Incremental Load via Time-Partitioned Dataset

Goal: write a pipeline that reads a CBN FX rate CSV and appends only new dates
into a local DuckDB table.

The key difference from week 1:
- The CSV now includes a rate_date column.
- You do NOT truncate the table on every run.
- Before inserting, check if this date is already in the table.
  If yes: skip. If no: insert.

Run it for Monday then Tuesday: both dates accumulate in the table.
Run it for Monday again: 0 rows inserted - it is idempotent per date.

The source: a dated CBN FX rate CSV with rate_date column, e.g.
    week_2_incremental_load_ingestion/data/cbn/cbn_fx_rates_2026-06-09.csv

The target: a local DuckDB file - cbn_fx_incremental.duckdb - in the current
directory.

Usage (run from the repo root):
    python week_2_incremental_load_ingestion/assignment/ingest.py \\
        week_2_incremental_load_ingestion/data/cbn/cbn_fx_rates_2026-06-09.csv

Verify:
    python -c "
    import duckdb
    conn = duckdb.connect('cbn_fx_incremental.duckdb')
    print(conn.execute('''
        SELECT rate_date, COUNT(*) as rows
        FROM cbn_fx_rates_partitioned
        GROUP BY rate_date
        ORDER BY rate_date
    ''').fetchdf())
    "

Reset between attempts:
    rm -f cbn_fx_incremental.duckdb
"""

import csv
import sys
from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# SQL - fill in the blanks
# ---------------------------------------------------------------------------

# TODO 1: Write the CREATE TABLE IF NOT EXISTS statement.
#   Add a rate_date column (DATE type) - this is what makes incremental load
#   possible. Other columns are the same as week 1:
#     currency_code     VARCHAR
#     currency          VARCHAR
#     buying_rate       DOUBLE
#     central_rate      DOUBLE
#     selling_rate      DOUBLE
#     is_forward_filled BOOLEAN
CREATE = """
-- TODO 1: write the CREATE TABLE IF NOT EXISTS statement here
"""

# TODO 2: Write the idempotency check.
#   Return the count of rows already in the table for a given rate_date.
#   If count > 0, this date has already been loaded - we skip it.
#   DuckDB uses ? as the placeholder for parameters.
CHECK = """
-- TODO 2: write SELECT COUNT(*) ... WHERE rate_date = ? here
"""

# TODO 3: Write the INSERT statement.
#   Use ? placeholders. Column order must match the tuple order you build in
#   load() - put rate_date first, then the remaining columns.
INSERT = """
-- TODO 3: write the INSERT statement here
"""


# ---------------------------------------------------------------------------
# Load function - fill in the blanks
# ---------------------------------------------------------------------------


def load(csv_path: Path) -> None:
    # TODO 4: Open csv_path and read it into a list of dicts.
    #   Use csv.DictReader - it turns each row into a dict keyed by the CSV
    #   header (currency_code, currency, rate_date, buying_rate, ...).
    rows: list[dict] = []  # replace this

    # TODO 5: The CSV stores is_forward_filled as the string "True" or "False".
    #   Convert it to a Python bool for every row before inserting.
    #   Hint: row["is_forward_filled"].lower() == "true"

    if not rows:
        print(f"No rows in {csv_path.name} - nothing to do")
        return

    # TODO 6: Extract rate_date from rows[0]["rate_date"].
    #   Every row in the file shares the same rate_date, so one lookup is enough.
    rate_date = None  # replace this

    # TODO 7: Open a DuckDB connection to "cbn_fx_incremental.duckdb".
    #   1. Run CREATE to ensure the table exists.
    #   2. Run CHECK with (rate_date,) as the parameter tuple.
    #   3. Fetch the result with .fetchone()[0] to get the count.
    #   4. If count > 0, print a "skipping" message and return.
    #   5. Otherwise build a list of tuples in this column order:
    #        (rate_date, currency_code, currency, buying_rate, central_rate,
    #         selling_rate, is_forward_filled)
    #      and insert all rows with conn.executemany(INSERT, tuples).
    #   6. Close the connection.
    #
    #   Pattern:
    #     conn = duckdb.connect("cbn_fx_incremental.duckdb")

    print(f"Loaded {len(rows)} rows for {rate_date} from {csv_path.name}")


# ---------------------------------------------------------------------------
# Entry point - no changes needed below this line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python ingest.py <path/to/cbn_fx_rates_YYYY-MM-DD.csv>")
    load(Path(sys.argv[1]))
