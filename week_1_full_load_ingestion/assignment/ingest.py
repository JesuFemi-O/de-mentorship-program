"""
Week 1 Assignment — Full-Load Ingestion with Snapshot History

Goal: build a full-load pipeline that accumulates one row per currency per day
instead of overwriting the table on every run.

The source: a folder of dated CBN FX rate CSVs, e.g.
    data/cbn/phase_1/cbn_fx_rates_2026-05-19.csv
    data/cbn/phase_1/cbn_fx_rates_2026-05-20.csv
    ...

Each file is a complete daily snapshot of 13 currencies. Your pipeline must:

  1. Read a single CSV file.
  2. Parse the snapshot date from the filename.
  3. Stamp every row with that snapshot_date.
  4. Delete any existing rows for that date (so re-running is safe).
  5. Insert all rows.

When you run the script for every file in the folder, the table should contain
the full week's history — one partition per snapshot_date.

Usage:
    python assignment/ingest.py data/cbn/phase_1/cbn_fx_rates_2026-05-19.csv
    python assignment/ingest.py data/cbn/phase_1/cbn_fx_rates_2026-05-20.csv
    ...

Verify with psql:
    SELECT snapshot_date, COUNT(*) FROM cbn_fx_rates GROUP BY 1 ORDER BY 1;

Expected: 7 rows (one per day), each with 13 currencies.

Reset between attempts:
    psql -c "DROP TABLE IF EXISTS cbn_fx_rates;"
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from shared.db import get_connection

# ---------------------------------------------------------------------------
# SQL — fill in the blanks
# ---------------------------------------------------------------------------

# TODO 1: Define the CREATE TABLE statement.
#   Columns needed:
#     currency_code     TEXT
#     currency          TEXT
#     buying_rate       NUMERIC(12, 4)
#     central_rate      NUMERIC(12, 4)
#     selling_rate      NUMERIC(12, 4)
#     is_forward_filled BOOLEAN
#     snapshot_date     DATE          ← this is the column that stores which
#                                        file the row came from
#
#   Use CREATE TABLE IF NOT EXISTS so the script is idempotent.
CREATE = """
-- TODO 1: write the CREATE TABLE IF NOT EXISTS statement here
"""

# TODO 2: Define the DELETE statement.
#   It should delete all rows where snapshot_date equals the date we are
#   about to load.  Use %(snapshot_date)s as the placeholder.
DELETE = """
-- TODO 2: write the DELETE statement here
"""

# TODO 3: Define the INSERT statement.
#   Insert one row with all columns, using %(column_name)s placeholders.
INSERT = """
-- TODO 3: write the INSERT statement here
"""


# ---------------------------------------------------------------------------
# Helpers — fill in the blanks
# ---------------------------------------------------------------------------


def parse_date(path: Path):
    """Extract the YYYY-MM-DD date from a filename like cbn_fx_rates_2026-05-19.csv."""
    import re
    from datetime import date

    # TODO 4: Use re.search to find the date pattern in path.name.
    #   Return a datetime.date object parsed with date.fromisoformat().
    #   Raise ValueError if no match is found.
    raise NotImplementedError("TODO 4: implement parse_date")


def load(csv_path: Path) -> None:
    # TODO 5: Parse the snapshot_date from csv_path using parse_date().
    snapshot_date = None  # replace this

    # TODO 6: Read the CSV file into a list of dicts (use csv.DictReader).
    rows = []  # replace this

    # TODO 7: For each row, convert is_forward_filled from the string "True"/"False"
    #   to a Python bool (hint: row["is_forward_filled"].lower() == "true").
    #   Also add snapshot_date to each row dict.

    # TODO 8: Open a database connection, create the table if it does not
    #   exist, delete existing rows for this snapshot_date, insert all rows,
    #   and commit.  Use get_connection() from shared.db.
    #
    #   Pattern:
    #     conn = get_connection()
    #     try:
    #         with conn.cursor() as cur:
    #             cur.execute(CREATE)
    #             cur.execute(DELETE, {"snapshot_date": snapshot_date})
    #             cur.executemany(INSERT, rows)
    #         conn.commit()
    #     finally:
    #         conn.close()

    print(f"Loaded {len(rows)} rows from {csv_path.name} (snapshot_date={snapshot_date})")


# ---------------------------------------------------------------------------
# Entry point — no changes needed below this line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python ingest.py <path/to/cbn_fx_rates_YYYY-MM-DD.csv>")
    load(Path(sys.argv[1]))
