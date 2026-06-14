"""
Generate CBN FX rate CSVs for the incremental-load lesson.

Produces two batches:
  - history/   3 months of weekday files (Jan-Mar 2026) - the "historical dump"
  - recent/    the current week - the "new daily files arriving incrementally"

Usage:
    python week_2_incremental_load_ingestion/setup_lesson.py

    # Custom history range
    python week_2_incremental_load_ingestion/setup_lesson.py \\
        --history-start 2026-01-01 --history-end 2026-03-31

    # Custom recent week
    python week_2_incremental_load_ingestion/setup_lesson.py --recent-week 2026-06-09
"""

import argparse
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
        rows, forward_filled = extract_for_date(all_records, current)
        if rows:
            write_csv(rows, current, output_dir, include_rate_date=True)
            written += 1
        current += timedelta(days=1)
    return written


if __name__ == "__main__":
    TODAY = date.today()
    parser = argparse.ArgumentParser(
        description="Generate CBN FX CSVs for the week 2 lesson (history + recent)"
    )
    parser.add_argument("--history-start", default="2026-01-01", metavar="YYYY-MM-DD")
    parser.add_argument("--history-end",   default="2026-03-31", metavar="YYYY-MM-DD")
    parser.add_argument("--recent-week",   default=None, metavar="YYYY-MM-DD",
                        help="Any date in the recent week (default: current week)")
    base = Path(__file__).parent / "data" / "cbn"
    args = parser.parse_args()

    history_start = date.fromisoformat(args.history_start)
    history_end   = date.fromisoformat(args.history_end)
    anchor        = date.fromisoformat(args.recent_week) if args.recent_week else TODAY
    recent_start  = anchor - timedelta(days=anchor.weekday())
    recent_end    = recent_start + timedelta(days=6)

    print("Fetching CBN rate history…")
    all_records = fetch_all_records()
    print(f"  {len(all_records)} records in model.\n")

    print(f"Generating history/  ({history_start} → {history_end})")
    n = generate_range(history_start, history_end, base / "history", all_records)
    print(f"  {n} files written.\n")

    print(f"Generating recent/   ({recent_start} → {recent_end})")
    n = generate_range(recent_start, recent_end, base / "recent", all_records)
    print(f"  {n} files written.\n")

    print(f"Done. Data in: {base.resolve()}")
