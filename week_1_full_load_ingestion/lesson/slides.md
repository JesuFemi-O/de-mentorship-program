---
marp: true
theme: default
paginate: true
---

# Week 1 - Full-Load Ingestion

## Data Engineering Design Patterns

60 min · discussion + live demo + Q&A

---

## The Scenario

> You're a data engineer at a fintech. The finance team needs daily NGN exchange rates in the warehouse so analysts can convert transaction amounts and reconcile accounts.
>
> The Central Bank of Nigeria publishes official rates every weekday. You get a fresh CSV each morning. **The file contains no information about what changed since yesterday - it is always a complete snapshot of that day's rates.**

**How do you keep this data fresh and queryable?**

---

## What Makes This Hard

The source gives you no help detecting changes:

- No `updated_at` column - you cannot filter for rows newer than your last run
- No version flag - you cannot compare versions to find what changed
- No CDC stream - the source does not emit change events
- No delta file - every delivery is a complete dump of current state

**You can't detect what changed. You only know what exists right now.**

---

## Our Dataset - CBN FX Rates

Central Bank of Nigeria official NGN exchange rates, published every weekday.

```text
currency_code  currency          buying_rate  central_rate  selling_rate  is_forward_filled
USD            Us Dollar         1369.8862    1370.3862     1370.8862     False
EUR            Euro              1601.8079    1602.3926     1602.9772     False
GBP            Pounds Sterling   1850.0313    1850.7066     1851.3818     False
...            (13 currencies total)
```

One file per day, named by date: `cbn_fx_rates_2026-05-14.csv`

> CBN does not publish on weekends. What do you think `is_forward_filled` means?

---

## Discussion

You receive a new file every weekday.

**How would you get this into a database reliably, every day?**

*Take 2 minutes - think about it.*

---

## 🖥️ Demo 1 - Build the Pipeline

1. Create the target table in Postgres
2. Write a script that reads a CSV and loads it
3. Run it for Monday's file
4. Query the table - what do you see?

---

## Check-in

We just loaded Monday's file.

Now we run the same script for **Tuesday's** file.

---

**What is in the table?**

---

## The Accounting Question

> "Hey - the finance team needs to reconcile last Thursday's GBP rate against a transaction that was processed that day. Can you pull it?"

You loaded Friday's file this morning.

**What happens when you query the table?**

---

## Discussion - The Data Is Gone

How do you fix this going forward?

*Take 2 minutes - propose a solution.*

- **Keep multiple tables?** One per day - gets unwieldy fast.
- **Add a date column?** But where does the date come from - the file doesn't have one.

> We'll explore the answer in week 2.

---

## The Pattern - Full Load

| Property         |                                                             |
| ---------------- | ----------------------------------------------------------- |
| Strategy         | Truncate target, insert full source snapshot                |
| Idempotent?      | Yes - run it twice, same result                             |
| History          | Not preserved - every load replaces the entire table        |
| Change detection | Not needed - you reload everything                          |
| Best fit         | Small reference data, complete snapshots, no delta available|

---

## When Full-Load Breaks Down

- **Dataset is large?** Reloading 100M rows daily is expensive - consider incremental.
- **Consumers need real-time?** Full-load is batch by nature.
- **Source produces deletes?** Full load handles them naturally. Incremental strategies often don't.
- **History must be preserved?** Full load alone can't give you this - you need a different pattern.
- **Source schema changes?** Your pipeline owns the contract - validate the file before loading.

---

## Next Week - Snapshot Load

Same dataset. Same source. Same pattern - but what if we stopped throwing history away?

---

## Assignment - due before next session

Two parts. Both live in `week_1_full_load_ingestion/assignment/`.

---

### Part 1 - Real-world reflection

Fill in `assignment/discussion.md`.

Find a real system, dataset, or workflow where full-load is either the right pattern or the wrong one. Come ready to present in 2-3 minutes:

1. **What is the source?** How is the data delivered?
2. **Why does full-load fit (or not fit)?** Think about size, frequency, history, and whether the source gives you change information.
3. **What breaks if you get it wrong?**

There is no right answer - the goal is to show your reasoning.

---

### Part 2 - Coding

Complete `assignment/ingest.py`.

Same full-load pattern from the demo, but against a local **DuckDB** file instead of Postgres. DuckDB needs no server - just `import duckdb` and open a file.

Six TODOs guide you:

1. Write the `CREATE TABLE IF NOT EXISTS` statement
2. Write the `TRUNCATE` statement
3. Write the `INSERT` statement using `?` placeholders
4. Read the CSV with `csv.DictReader`
5. Coerce `is_forward_filled` from string `"True"`/`"False"` to `bool`
6. Open a DuckDB connection and run `CREATE` → `TRUNCATE` → `INSERT`

Run it:

```bash
python week_1_full_load_ingestion/assignment/ingest.py \
    week_1_full_load_ingestion/data/cbn/cbn_fx_rates_2026-06-04.csv
```

Verify:

```python
python -c "
import duckdb
conn = duckdb.connect('cbn_fx.duckdb')
print(conn.execute('SELECT * FROM cbn_fx_rates').fetchdf())
"
```

You should see 13 rows. Run a different day's file - what happened to the first day's data?
