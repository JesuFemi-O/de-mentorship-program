# Week 2 - Incremental Load via Time-Partitioned Dataset

## The pattern

An **incremental load** appends only new data to the target table. Unlike a full load, it never truncates - it accumulates history.

This variant works when the source data carries a **date column** that identifies which partition each row belongs to. That date is the partition key. Before inserting, check whether the target already has rows for that date. If yes: skip. If no: insert.

This is the right choice when:

- The source publishes a daily snapshot and includes a date column in the data
- The business needs to query historical data, not just the latest state
- The dataset is stable within a given date - re-running for the same date should be a no-op

The tradeoff: if the source sends corrections for a date you have already loaded, a plain insert will silently miss them. And this pattern cannot propagate source deletes.

---

## The dataset

Same CBN FX rates as week 1, but the CSV now includes a `rate_date` column.

| Field               | Description                                                                                                      |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `currency_code`     | ISO 4217 code (e.g. `USD`, `EUR`)                                                                                |
| `currency`          | CBN display name                                                                                                 |
| `rate_date`         | The date these rates were published (the partition key)                                                          |
| `buying_rate`       | Bank buying rate                                                                                                 |
| `central_rate`      | Mid-market rate                                                                                                  |
| `selling_rate`      | Bank selling rate                                                                                                |
| `is_forward_filled` | `True` if CBN did not publish that day and the previous weekday's rate was carried forward                       |

---

## Source to target

| Source (CSV column)   | Target column            | Notes                                                         |
| --------------------- | ------------------------ | ------------------------------------------------------------- |
| `currency_code`       | `currency_code`          | Direct copy                                                   |
| `currency`            | `currency`               | Direct copy                                                   |
| `rate_date`           | `rate_date`              | Partition key - used to detect already-loaded dates           |
| `buying_rate`         | `buying_rate`            | Direct copy                                                   |
| `central_rate`        | `central_rate`           | Direct copy                                                   |
| `selling_rate`        | `selling_rate`           | Direct copy                                                   |
| `is_forward_filled`   | `is_forward_filled`      | Cast from string `"True"`/`"False"` to `BOOLEAN`              |

---

## Setup

Generate one week of dated CSV files (with `rate_date` column) before the lesson:

```bash
# Current week (default)
python week_2_incremental_load_ingestion/setup_lesson.py

# A specific week - pass any date in that week
python week_2_incremental_load_ingestion/setup_lesson.py --week 2026-06-09

# Write to a custom directory
python week_2_incremental_load_ingestion/setup_lesson.py --output-dir /tmp/cbn_w2
```

This writes seven files - Monday through Sunday - to `week_2_incremental_load_ingestion/data/cbn/`:

```text
cbn_fx_rates_2026-06-08.csv   <- Monday    (published)
cbn_fx_rates_2026-06-09.csv   <- Tuesday   (published)
cbn_fx_rates_2026-06-10.csv   <- Wednesday (published)
cbn_fx_rates_2026-06-11.csv   <- Thursday  (published)
cbn_fx_rates_2026-06-12.csv   <- Friday    (published)
cbn_fx_rates_2026-06-13.csv   <- Saturday  (forward-filled from Friday)
cbn_fx_rates_2026-06-14.csv   <- Sunday    (forward-filled from Friday)
```

Each file now includes a `rate_date` column in the data itself.

---

## In-session live coding

### Demo - Build the incremental pipeline

The instructor adds `rate_date` to the table, writes the idempotency check, and loads two consecutive days - observing that history accumulates and the same file run twice is a no-op.

```sql
CREATE TABLE IF NOT EXISTS cbn_fx_rates_partitioned (
    rate_date         DATE,
    currency_code     TEXT,
    currency          TEXT,
    buying_rate       NUMERIC(12, 4),
    central_rate      NUMERIC(12, 4),
    selling_rate      NUMERIC(12, 4),
    is_forward_filled BOOLEAN
);
```

The reference solution is in [`solutions/v1_incremental_load.py`](solutions/v1_incremental_load.py).

---

## Connecting to Postgres

Use the shared connection helper:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from shared.db import get_connection

conn = get_connection()
```

Default credentials (from `.env.example`): `postgres / postgres` on `localhost:5432`, database `de_mentorship`.

---

## Assignment (due before next session)

### Part 1 - Real-world reflection

Fill in [`assignment/discussion.md`](assignment/discussion.md) and come to the next session ready to present in 2-3 minutes.

### Part 2 - Coding

Complete the skeleton in [`assignment/ingest.py`](assignment/ingest.py).

Same incremental-load pattern from the demo, but written against a local **DuckDB** file (`cbn_fx_incremental.duckdb`) instead of Postgres.

Seven TODOs guide you:

| TODO | What to do                                                                          |
| ---- | ----------------------------------------------------------------------------------- |
| 1    | Write `CREATE TABLE IF NOT EXISTS` with `rate_date DATE`                            |
| 2    | Write the `CHECK` query (`SELECT COUNT(*) ... WHERE rate_date = ?`)                 |
| 3    | Write the `INSERT` statement using `?` placeholders                                 |
| 4    | Read the CSV into a list of dicts with `csv.DictReader`                             |
| 5    | Coerce `is_forward_filled` from string to `bool`                                    |
| 6    | Extract `rate_date` from `rows[0]`                                                  |
| 7    | Open DuckDB, run `CREATE` -> `CHECK` -> insert or skip                              |

Pick two files from `data/cbn/` and run them in sequence. Verify with:

```python
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
```

You should see one row per loaded date. Run the same file twice - what happens?

Reset between attempts by deleting `cbn_fx_incremental.duckdb`.
