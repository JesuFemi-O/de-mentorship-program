"""
Generate CBN FX rate CSVs for the incremental-load lesson.

Always produces two batches relative to today:
  - history/   1 Jan of the current year  ->  today - 7 days
  - recent/    today - 6 days             ->  today

Run it any day and it produces the right data for that day's lesson.

Usage:
    python week_2_incremental_load_ingestion/setup_lesson.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from shared.cbn.ingest_cbn_fx import fetch_all_records, extract_for_date, write_csv


def generate_range(start: date, end: date, output_dir: Path, all_records: list) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    current = start
    while current <= end:
        rows, _ = extract_for_date(all_records, current)
        if rows:
            write_csv(rows, current, output_dir, include_rate_date=True)
            written += 1
        current += timedelta(days=1)
    return written


if __name__ == "__main__":
    today = date.today()

    # Most recent weekday (today if Mon-Fri, else last Friday)
    days_back = max(1, today.weekday() - 4) if today.weekday() >= 5 else 0
    last_weekday = today - timedelta(days=days_back) if today.weekday() >= 5 else today

    history_start = date(today.year, 1, 1)
    history_end   = last_weekday - timedelta(days=1)
    recent_start  = last_weekday
    recent_end    = last_weekday

    base = Path(__file__).parent / "data" / "cbn"

    print("Fetching CBN rate history...")
    all_records = fetch_all_records()
    print(f"  {len(all_records)} records in model.\n")

    print(f"Generating history/  ({history_start} -> {history_end})")
    n = generate_range(history_start, history_end, base / "history", all_records)
    print(f"  {n} files written.\n")

    print(f"Generating recent/   ({recent_start} -> {recent_end})")
    n = generate_range(recent_start, recent_end, base / "recent", all_records)
    print(f"  {n} files written.\n")

    print(f"Done. Data in: {base.resolve()}")
