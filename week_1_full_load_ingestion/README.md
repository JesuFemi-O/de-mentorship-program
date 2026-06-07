# Week 1 - Full-Load Ingestion

## The pattern

A **full load** replaces the entire target table with the latest snapshot from the source on every run. There is no tracking of what changed - you simply truncate and reload.

This is the right choice when:

- The source publishes a complete daily snapshot (not a delta)
- The dataset is small enough that reloading everything is cheap
- You need the simplest possible pipeline with no state to manage

The tradeoff is that you lose history on every load unless your target schema is designed to keep it (e.g. partitioned by `snapshot_date`).

---

## The dataset

CBN (Central Bank of Nigeria) official NGN exchange rates - 13 currencies, one snapshot per weekday.

| Field | Description |
| --- | --- |
| `currency_code` | ISO 4217 code (e.g. `USD`, `EUR`) |
| `currency` | CBN display name |
| `rate_date` | Date the rate was published |
| `buying_rate` | Bank buying rate |
| `central_rate` | Mid-market rate |
| `selling_rate` | Bank selling rate |
| `is_forward_filled` | `True` if the CBN did not publish that day (weekend/holiday) and the previous weekday's rate was carried forward |

CBN does not publish on weekends or public holidays. Saturday and Sunday files carry Friday's rates with `is_forward_filled=True`. Your pipeline should handle this transparently - do not skip or drop forward-filled rows.

---

## Setup

Generate one week of dated CSV files before the lesson:

```bash
# Current week (default)
python week_1_full_load_ingestion/setup_lesson.py

# A specific week - pass any date in that week
python week_1_full_load_ingestion/setup_lesson.py --week 2026-05-11

# Write to a custom directory
python week_1_full_load_ingestion/setup_lesson.py --output-dir /tmp/cbn
```

This writes seven files - Monday through Sunday - to `week_1_full_load_ingestion/data/cbn/`:

```text
cbn_fx_rates_2026-05-11.csv   ← Monday   (published)
cbn_fx_rates_2026-05-12.csv   ← Tuesday  (published)
cbn_fx_rates_2026-05-13.csv   ← Wednesday (published)
cbn_fx_rates_2026-05-14.csv   ← Thursday (published)
cbn_fx_rates_2026-05-15.csv   ← Friday   (published)
cbn_fx_rates_2026-05-16.csv   ← Saturday (forward-filled from Friday)
cbn_fx_rates_2026-05-17.csv   ← Sunday   (forward-filled from Friday)
```

The setup script has no network dependency and no required input files. The same `--week` argument always produces byte-identical output - run it as many times as needed.

---

## In-session live coding

The coding happens during the session, not as homework. You follow along on your own machine as the instructor builds the pipeline live.

### Demo 1 — Build the pipeline

The instructor creates the target table and writes a script that reads a CSV and loads it. You run it for Monday's file, then query the table.

```sql
CREATE TABLE fx_rates_full (
    currency_code     VARCHAR(10)    NOT NULL,
    currency          VARCHAR(50)    NOT NULL,
    buying_rate       NUMERIC(18, 4) NOT NULL,
    central_rate      NUMERIC(18, 4) NOT NULL,
    selling_rate      NUMERIC(18, 4) NOT NULL,
    is_forward_filled BOOLEAN        NOT NULL
);
```

### Demo 2 — The snapshot solution

The instructor adds a `snapshot_date` column, parsed from the filename, and reloads the full week. You then query for a specific day's rate.

Solutions for both demos live in `solutions/` if you want to review them after the session.

---

## Connecting to Postgres

Use the shared connection helper:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from shared.db import get_connection

with get_connection() as conn:
    ...
```

Default credentials (from `.env.example`): `postgres / postgres` on `localhost:5432`, database `cdcdemo`.

---

## Assignment (due before next session)

### Part 1 — Coding

Complete the skeleton in [`assignment/ingest.py`](assignment/ingest.py).

It builds on Demo 2: your goal is a full-load pipeline that accumulates history instead of overwriting the table on every run.

Eight TODOs guide you through the implementation:

| TODO | What to do |
| --- | --- |
| 1 | Write the `CREATE TABLE IF NOT EXISTS` statement with all columns including `snapshot_date` |
| 2 | Write the `DELETE` statement that removes existing rows for a given `snapshot_date` |
| 3 | Write the `INSERT` statement |
| 4 | Implement `parse_date()` to extract the date from the filename |
| 5–8 | Implement `load()` — read the CSV, coerce types, and write to Postgres |

Run it for every file in `data/cbn/phase_1/` and verify with:

```sql
SELECT snapshot_date, COUNT(*) FROM cbn_fx_rates GROUP BY 1 ORDER BY 1;
```

You should see 7 rows, each with 13 currencies. The reference solution is in `solutions/v2_snapshot_load.py` — try not to peek until you're done.

### Part 2 — Real-world reflection

Fill in [`assignment/discussion.md`](assignment/discussion.md) and come to the next session ready to present in 2–3 minutes.

There is no right answer — the goal is to show your reasoning, not to find a textbook example.
