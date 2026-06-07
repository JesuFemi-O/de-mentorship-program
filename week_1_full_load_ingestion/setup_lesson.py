"""
Generate two sets of CBN FX rate CSVs for the full-load lesson.

Phase 1 — no rate_date column (used for Demo 1 and Demo 2)
Phase 2 — includes rate_date column (used for Act 3 — schema evolution)

Each phase covers Monday through Sunday of the target week so students
always get both weekday and forward-filled weekend rows.

Usage:
    python week_1_full_load_ingestion/setup_lesson.py              # current week
    python week_1_full_load_ingestion/setup_lesson.py --week 2026-01-05
    python week_1_full_load_ingestion/setup_lesson.py --output-dir data/cbn

Files written:
    <output_dir>/phase_1/cbn_fx_rates_YYYY-MM-DD.csv  (× 7, no rate_date)
    <output_dir>/phase_2/cbn_fx_rates_YYYY-MM-DD.csv  (× 7, with rate_date)
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from shared.cbn.ingest_cbn_fx import fetch_all_records, extract_for_date, write_csv


def generate_phase(all_records: list, monday: date, output_dir: Path, include_rate_date: bool) -> None:
    for offset in range(7):
        day = monday + timedelta(days=offset)
        rows, forward_filled = extract_for_date(all_records, day)
        if not rows:
            print(f"  {day}  - no data available, skipping")
            continue
        label = "forward-filled from " + rows[0]["rate_date"] if forward_filled else "published"
        csv_path = write_csv(rows, day, output_dir, include_rate_date=include_rate_date)
        print(f"  {day}  {len(rows)} currencies ({label}) → {csv_path.name}")


def generate_week(monday: date, output_dir: Path) -> None:
    print("Fetching CBN rate history…")
    all_records = fetch_all_records()
    print(f"  {len(all_records)} records generated.\n")

    print("Phase 1 — no rate_date (for Demo 1 and Demo 2):")
    generate_phase(all_records, monday, output_dir / "phase_1", include_rate_date=False)

    print("\nPhase 2 — with rate_date (for Act 3):")
    generate_phase(all_records, monday, output_dir / "phase_2", include_rate_date=True)

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
        help="Parent directory for phase_1/ and phase_2/ folders (default: %(default)s)",
    )
    args = parser.parse_args()

    anchor = date.fromisoformat(args.week)
    if anchor > CURRENT_DATE:
        parser.error(f"--week must not be a future date (got {anchor}, today is {CURRENT_DATE})")
    if anchor.weekday() >= 5:
        print("Note: date falls on a weekend — week will include forward-filled rows for Saturday/Sunday.")
    start_date = anchor - timedelta(days=anchor.weekday())
    generate_week(start_date, Path(args.output_dir))
