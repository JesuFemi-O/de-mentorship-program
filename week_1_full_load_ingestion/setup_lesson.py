"""
Generate a week of CBN FX rate CSVs for the full-load lesson.

Each file covers one day (Monday through Sunday) so students get both
weekday and forward-filled weekend rows.

Usage:
    python week_1_full_load_ingestion/setup_lesson.py              # current week
    python week_1_full_load_ingestion/setup_lesson.py --week 2026-01-05
    python week_1_full_load_ingestion/setup_lesson.py --output-dir /tmp/cbn

Files written to <output_dir>/:
    cbn_fx_rates_YYYY-MM-DD.csv  (one per day, Monday through Sunday)
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from shared.cbn.ingest_cbn_fx import fetch_all_records, extract_for_date, write_csv


def generate_week(monday: date, output_dir: Path) -> None:
    print("Fetching CBN rate history…")
    all_records = fetch_all_records()
    print(f"  {len(all_records)} records generated.\n")

    for offset in range(7):
        day = monday + timedelta(days=offset)
        rows, forward_filled = extract_for_date(all_records, day)
        if not rows:
            print(f"  {day}  - no data available, skipping")
            continue
        label = "forward-filled from " + rows[0]["rate_date"] if forward_filled else "published"
        csv_path = write_csv(rows, day, output_dir, include_rate_date=False)
        print(f"  {day}  {len(rows)} currencies ({label}) → {csv_path.name}")

    print(f"\nDone. Files written to: {output_dir.resolve()}")


if __name__ == "__main__":
    CURRENT_DATE = date.today()
    parser = argparse.ArgumentParser(
        description="Generate CBN FX rate CSVs for the full-load lesson"
    )
    parser.add_argument(
        "--week",
        metavar="YYYY-MM-DD",
        help="Any date in the target week (default: current week)",
    )
    default_output_dir = Path(__file__).parent / "data" / "cbn"
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir),
        metavar="DIR",
        help="Directory to write CSV files to (default: %(default)s)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    anchor = date.fromisoformat(args.week) if args.week else CURRENT_DATE
    if anchor > CURRENT_DATE:
        parser.error(f"--week must not be a future date (got {anchor}, today is {CURRENT_DATE})")
    if anchor.weekday() >= 5:
        print("Note: date falls on a weekend - week will include forward-filled rows for Saturday/Sunday.")
    start_date = anchor - timedelta(days=anchor.weekday())
    generate_week(start_date, output_dir)
