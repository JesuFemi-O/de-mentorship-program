"""
Generate one week of CBN FX rate CSVs for the full-load lesson.

Run this once before the lesson to create seven dated CSV files - Monday
through Sunday - so every student starts with identical data.  The week
always includes Saturday and Sunday to give you forward-filled rows (CBN
does not publish on weekends), which makes the full-load mechanics visible.

Fetches the CBN rate history in a single API call, then extracts the
correct published rate for each day from the local copy - no repeated
network requests.

Usage:
    python 01_data_ingestion_full_load/setup_lesson.py                     # demo week
    python 01_data_ingestion_full_load/setup_lesson.py --week 2026-01-05   # any Monday
    python 01_data_ingestion_full_load/setup_lesson.py --output-dir data/cbn

Files written:
    data/cbn/cbn_fx_rates_YYYY-MM-DD.csv  (× 7)
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))

from shared.cbn.ingest_cbn_fx import fetch_all_records, extract_for_date, write_csv

# A Monday in a week where CBN published on all five business days.
DEMO_WEEK_MONDAY = date(2026, 5, 4)


def generate_week(monday: date, output_dir: Path) -> None:
    print("Fetching CBN rate history (one request for all 7 days)…")
    all_records = fetch_all_records()
    print(f"  {len(all_records)} records fetched.\n")

    for offset in range(7):
        day = monday + timedelta(days=offset)
        rows, forward_filled = extract_for_date(all_records, day)
        if not rows:
            print(f"  {day}  - no data available, skipping")
            continue
        label = "forward-filled from " + rows[0]["rate_date"] if forward_filled else "published"
        csv_path = write_csv(rows, day, output_dir)
        print(f"  {day}  {len(rows)} currencies ({label}) → {csv_path.name}")

    print(f"\nDone. Files written to: {output_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a week of CBN FX rate CSVs for the full-load lesson"
    )
    parser.add_argument(
        "--week",
        default=DEMO_WEEK_MONDAY.isoformat(),
        metavar="YYYY-MM-DD",
        help="Monday of the desired week (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/cbn",
        metavar="DIR",
        help="Directory to write CSV files (default: %(default)s)",
    )
    args = parser.parse_args()

    monday = date.fromisoformat(args.week)
    if monday.weekday() != 0:
        parser.error(f"{args.week} is not a Monday (weekday={monday.weekday()})")

    generate_week(monday, Path(args.output_dir))
