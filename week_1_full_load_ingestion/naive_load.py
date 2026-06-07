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
-- TODO 1: write the CREATE TABLE IF NOT EXISTS statement here
"""

# TODO 2: Write the TRUNCATE statement.
#   This wipes the whole table before every load - that is what makes it
#   "naive".  A single SQL keyword is enough.
TRUNCATE = """
-- TODO 2: write the TRUNCATE statement here
"""

# TODO 3: Write the INSERT statement.
#   Insert one row using %(column_name)s placeholders for each column.
#   The column names must match the keys in the row dicts you will build
#   from the CSV.
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
    rows = []  # replace this

    # TODO 5: The CSV stores is_forward_filled as the string "True" or "False".
    #   Convert it to a Python bool for every row before inserting.
    #   Hint: row["is_forward_filled"].lower() == "true"

    # TODO 6: Open a database connection and run the three SQL statements in
    #   order - CREATE, TRUNCATE, then INSERT all rows - then commit.
    #
    #   Pattern to follow:
    #     conn = get_connection()
    #     try:
    #         with conn.cursor() as cur:
    #             cur.execute(CREATE)
    #             cur.execute(TRUNCATE)
    #             cur.executemany(INSERT, rows)
    #         conn.commit()
    #     finally:
    #         conn.close()

    print(f"Loaded {len(rows)} rows from {csv_path.name}")


# ---------------------------------------------------------------------------
# Entry point - no changes needed below this line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python naive_load.py <path/to/cbn_fx_rates_YYYY-MM-DD.csv>")
    load(Path(sys.argv[1]))
