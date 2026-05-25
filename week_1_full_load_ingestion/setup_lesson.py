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
    python week_1_full_load_ingestion/setup_lesson.py              # current week
    python week_1_full_load_ingestion/setup_lesson.py --week 2026-01-05 # any date in the target week
    python week_1_full_load_ingestion/setup_lesson.py --output-dir data/cbn

Files written:
    data/cbn/cbn_fx_rates_YYYY-MM-DD.csv  (× 7)
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from shared.cbn.ingest_cbn_fx import fetch_all_records, extract_for_date, write_csv

def generate_week(monday: date, output_dir: Path) -> None:
    print("Generating CBN rate history for all 7 days…")
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
    CURRENT_DATE = date.today()
    parser = argparse.ArgumentParser(
        description="Generate a week of CBN FX rate CSVs for the full-load lesson"
    )
    parser.add_argument(
        "--week",
        default=CURRENT_DATE.isoformat(),
        metavar="YYYY-MM-DD",
        help="Any date in the target week (default: %(default)s)",
    )
    default_output_dir = Path(__file__).parent / "data" / "cbn"
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir),
        metavar="DIR",
        help="Directory to write CSV files (default: %(default)s)",
    )
    args = parser.parse_args()

    anchor = date.fromisoformat(args.week)
    if anchor > CURRENT_DATE:
        parser.error(f"--week must not be a future date (got {anchor}, today is {CURRENT_DATE})")
    if anchor.weekday() >= 5:
        print("Note: date falls on a weekend — week will include forward-filled rows for Saturday/Sunday.")
    start_date = anchor - timedelta(days=anchor.weekday())
    generate_week(start_date, Path(args.output_dir))
