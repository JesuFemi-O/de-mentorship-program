---
marp: true
theme: default
paginate: true
---

# Week 2 - Incremental Load

## Data Engineering Design Patterns

60 min · discussion + two demos + Q&A

---

## Picking Up From Week 1

Full load: TRUNCATE then INSERT everything.

Simple. Works. But **throws away history on every run**.

This week: two patterns that fix that, using two different datasets and two different delivery mechanisms.

---

## The Two Scenarios

| | Demo 1 | Demo 2 |
| --- | --- | --- |
| **Source** | CBN FX rates | ClearWatch watchlist |
| **Delivery** | File batch (CSV) | SFTP drop |
| **Pattern** | Append by date | Upsert by entity ID |
| **Key question** | "What was the USD rate on 15 March?" | "Is this entity currently sanctioned?" |

---

## Demo 1 - CBN Historical Snapshot + Incremental Load

---

## The Scenario - CBN

> The Central Bank of Nigeria hands you a historical dump: exchange rates for every weekday going back to January 2026. A new file will arrive each morning from today onwards.
>
> How do you load the history, and how do you keep it current?

---

## The Dataset - CBN

Same CBN FX rates as week 1 - but now the CSV includes `rate_date`.

```
currency_code, currency, rate_date,   buying_rate, central_rate, ...
USD,          Us Dollar, 2026-01-06,  1371.42,    1371.92,     ...
USD,          Us Dollar, 2026-01-07,  1368.77,    1369.27,     ...
...
```

`rate_date` is the **partition key** - it identifies which day each row belongs to.

---

## The Strategy

Before inserting any file:

```sql
SELECT COUNT(*) FROM cbn_fx_rates_partitioned WHERE rate_date = '2026-01-06';
```

- Count = 0 → this date is new → INSERT 13 rows
- Count > 0 → already loaded → skip

Same logic handles the historical backfill and the daily run.

---

## 🖥️ Demo 1a - Backfill

```bash
python week_2_incremental_load_ingestion/incremental_load.py \
    week_2_incremental_load_ingestion/data/cbn/history/
```

Observe: 65+ dates loaded. Query any of them.

```sql
SELECT rate_date, currency_code, central_rate
FROM cbn_fx_rates_partitioned
WHERE currency_code = 'USD'
ORDER BY rate_date
LIMIT 5;
```

---

## 🖥️ Demo 1b - Daily Run

```bash
python week_2_incremental_load_ingestion/incremental_load.py \
    week_2_incremental_load_ingestion/data/cbn/recent/cbn_fx_rates_2026-06-09.csv
```

Only 13 rows inserted. Everything from the backfill is untouched.

Run it again - what happens?

---

## Check-in - Demo 1

```sql
SELECT COUNT(DISTINCT rate_date) FROM cbn_fx_rates_partitioned;
```

What do you expect after the backfill + one daily file?

---

## The Pattern - Time-Partitioned Incremental

| Property    |                                                          |
| ----------- | -------------------------------------------------------- |
| Strategy    | Append rows for dates not yet in the target              |
| Idempotent? | Yes - same date run twice, 0 rows inserted               |
| History     | Preserved - each date is a permanent partition           |
| Key column  | `rate_date` in the source data                           |
| Best fit    | Time-series snapshots where the date is in the data      |

---

## Demo 2 - ClearWatch Watchlist Upsert via SFTP

---

## The Scenario - ClearWatch

> NaijaPave subscribes to ClearWatch, an AML/sanctions data vendor. Every morning they upload a complete watchlist snapshot to your SFTP server - all sanctioned persons, PEPs, high-risk entities.
>
> The file is always a **full dump**. It does not tell you what changed.
>
> How do you keep the database current without loading duplicates?

---

## The Dataset - ClearWatch

```text
vendor_entity_id, entity_name,        watchlist_type,  risk_category, status
CW-000001,        Adaeze Okonkwo,     SANCTIONS,       HIGH,          ACTIVE
CW-000002,        Pinnacle Trade Ltd, PEP,             MEDIUM,        ACTIVE
CW-000003,        Emeka Nwosu,        ADVERSE_MEDIA,   LOW,           INACTIVE
```

`vendor_entity_id` is stable across deliveries - same entity, same ID, every day.

---

## Discussion

ClearWatch sends 50 records today. Tomorrow they send 50 records again.

- Some entities are new.
- Some changed `status` (ACTIVE → INACTIVE).
- Some have a new `last_reviewed_date`.

**If you use full load, what do you lose?**

**If you use time-partition, what breaks?**

*Take 2 minutes.*

---

## The Strategy - Upsert

```sql
INSERT INTO clearwatch_watchlist (vendor_entity_id, entity_name, status, ...)
VALUES (...)
ON CONFLICT (vendor_entity_id) DO UPDATE SET
    status             = EXCLUDED.status,
    risk_category      = EXCLUDED.risk_category,
    last_reviewed_date = EXCLUDED.last_reviewed_date,
    loaded_at          = NOW();
```

- Entity not in table → INSERT
- Entity already there → UPDATE mutable fields only
- `listed_date` is never overwritten - it records first appearance

---

## 🖥️ Demo 2 - Upsert Pipeline

```bash
# Simulate Monday's vendor delivery to SFTP
python shared/clearwatch/simulate_vendor_day.py --date 2021-01-04

# Run the upsert pipeline
python week_2_incremental_load_ingestion/sftp_upsert.py

# Simulate Tuesday (some entities change status)
python shared/clearwatch/simulate_vendor_day.py --date 2021-01-05

# Run again - observe updates
python week_2_incremental_load_ingestion/sftp_upsert.py
```

---

## Check-in - Demo 2

After loading Monday then Tuesday:

```sql
SELECT entity_name, status, last_reviewed_date, loaded_at
FROM clearwatch_watchlist
WHERE status = 'INACTIVE'
LIMIT 5;
```

How is this different from full load?

---

## Comparing the Two Patterns

| | Time-partitioned | Upsert |
| --- | --- | --- |
| **Key** | `rate_date` | `vendor_entity_id` |
| **New rows** | Inserted under new partition | Inserted |
| **Changed rows** | Not applicable | Updated in-place |
| **Deleted rows** | Not applicable | Vendor marks `status=INACTIVE` |
| **History** | Full history by date | Current state only |

---

## What Both Patterns Can't Do

Neither can tell you the **history of individual field changes**:

- When did entity CW-000001 change from ACTIVE to INACTIVE?
- What was the `risk_category` of this entity three weeks ago?

For that you need **change capture at the source**.

That is week 3.

---

## Assignment - due before next session

Two parts. Both live in `week_2_incremental_load_ingestion/assignment/`.

---

### Part 1 - Real-world reflection

Fill in `assignment/discussion.md`.

Find a dataset where one of today's patterns fits. Present in 2-3 minutes:

1. What is the source and how is it delivered?
2. Which pattern fits - time-partitioned or upsert? What is the key column?
3. What breaks if you use the wrong one?

---

### Part 2 - Coding

Complete `assignment/ingest.py`.

ClearWatch upsert, but against a local **DuckDB** file, reading from a local CSV (no SFTP needed).

Six TODOs guide you through: CREATE TABLE, INSERT OR REPLACE, reading the CSV, coercing nulls, building tuples, and running the pipeline.
