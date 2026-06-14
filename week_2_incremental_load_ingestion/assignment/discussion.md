# Week 2 Discussion - Incremental Load in the Wild

Find a real system, dataset, or workflow - from your job, a side project, or something you've read about - where incremental load via a time-partitioned dataset is either the right pattern or the wrong one.

Come to the next session ready to present in 2-3 minutes. Fill in your answers here before the session.

---

## 1. What is the source?

> Describe the data: what it contains, how it is delivered (API, file drop, database export, etc.), how often it is published, and roughly how large it is.
> Does the source include a date or timestamp in the data itself - or only in the filename?

_Your answer here._

---

## 2. Why does incremental load fit - or not fit?

> Think about:
> - **Date in the data** - does the source include a date or timestamp column you can use as a partition key? If not, where does the date come from?
> - **History** - does the business need to query data from previous days, weeks, or months? Or only the current state?
> - **Size** - is the daily volume small enough that reloading everything would work, or does incremental become necessary?
> - **Idempotency** - if your pipeline runs twice for the same date, what happens? Does the pattern protect you?

_Your answer here._

---

## 3. What breaks if you get the pattern wrong?

> Pick the wrong pattern and reason through the failure mode:
> - If you used full-load instead of incremental - what data do you lose?
> - If you used incremental but the source does not include a reliable date column - what goes wrong?

_Your answer here._

---

## Example (do not copy - find your own)

**Source:** A payment processor exports a daily CSV of completed transactions. Each row has a `settlement_date` column (the date the transaction cleared). Files arrive every morning and cover the previous business day.

**Why incremental fits:** The `settlement_date` column is in the data itself, making it a natural partition key. Finance needs to query any historical settlement date for reconciliation - a full load would destroy that history every morning. The daily file is ~500 000 rows, which is acceptable to insert incrementally but expensive to reload from scratch.

**What breaks if you get it wrong:** If you use full-load, every morning's run overwrites the entire table with the previous day's transactions only. Any query for data older than 24 hours returns nothing. The finance team's month-end reconciliation reports break immediately.
