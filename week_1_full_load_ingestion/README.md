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
| `snapshot_date` | The date the file represents |

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

## Exercise

Implement a full-load ingestion script that processes one CSV file per run.

### Target table

Create this table in the `public` schema of the local Postgres instance:

```sql
CREATE TABLE fx_rates_full (
    currency_code     VARCHAR(10)    NOT NULL,
    currency          VARCHAR(50)    NOT NULL,
    rate_date         DATE           NOT NULL,
    buying_rate       NUMERIC(18, 4) NOT NULL,
    central_rate      NUMERIC(18, 4) NOT NULL,
    selling_rate      NUMERIC(18, 4) NOT NULL,
    is_forward_filled BOOLEAN        NOT NULL,
    snapshot_date     DATE           NOT NULL
);
```

### What your script should do

1. Accept a `--date YYYY-MM-DD` argument identifying which CSV to load
2. Read the corresponding file from `data/cbn/`
3. **Truncate** `fx_rates_full`
4. Insert all 13 rows from the CSV
5. Be idempotent - running it twice for the same date leaves the table in the same state

### Key questions to answer

- What happens when you run the load for Monday, then run it again for Tuesday? What is in the table?
- What should you do differently if you want to keep all seven days in the table at once?
- Does `is_forward_filled=True` require any special handling in your load logic, or is it just another column?

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
