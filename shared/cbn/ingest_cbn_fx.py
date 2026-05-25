"""
Generates CBN-style NGN exchange rate CSVs from a seeded synthetic model.

This is a course data-preparation script - it produces the source file
students will use in the full-load lesson.  Loading into the warehouse
is the student exercise.

Rates are derived from a real 2026-05-14 CBN snapshot and vary day-to-day
via a date-seeded RNG (±0.8% per currency per day), so the same date always
produces identical output (idempotent) but adjacent days differ visibly.

Weekend / public-holiday handling: weekends are omitted from the synthetic
history so the forward-fill logic triggers naturally for Saturday/Sunday.

Usage:
    python ingest_cbn_fx.py                           # today
    python ingest_cbn_fx.py --date 2025-01-15         # specific date
    python ingest_cbn_fx.py --date 2025-01-15 --output-dir data/cbn
    python ingest_cbn_fx.py --dry-run                 # print, no files
"""

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

# Maps CBN currency name (title-cased) → ISO 4217 code
# Must stay in sync with cbn_currency_map seed in infrastructure/postgres/init.sql
CBN_CURRENCY_MAP: dict[str, str] = {
    "Cfa":                "XOF",
    "Yuan/Renminbi":      "CNY",
    "Danish Krona":       "DKK",
    "Euro":               "EUR",
    "Yen":                "JPY",
    "Riyal":              "SAR",
    "South African Rand": "ZAR",
    "Sdr":                "XDR",
    "Swiss Franc":        "CHF",
    "Pounds Sterling":    "GBP",
    "Us Dollar":          "USD",
    "Waua":               "WAU",
    "Uae Dirham":         "AED",
}

# Baseline rates anchored to the real 2026-05-14 CBN snapshot.
# Tuple: (central_rate, half_spread)  — buying = central - spread, selling = central + spread.
_BASE_RATES: dict[str, tuple[float, float]] = {
    "Cfa":                (2.4368,    0.0100),
    "Yuan/Renminbi":      (201.9670,  0.0737),
    "Danish Krona":       (214.4143,  0.0782),
    "Euro":               (1602.3926, 0.5847),
    "Yen":                (8.6794,    0.0032),
    "Riyal":              (365.1734,  0.1332),
    "South African Rand": (83.2035,   0.0304),
    "Sdr":                (1882.0610, 0.6867),
    "Swiss Franc":        (1751.5161, 0.6391),
    "Pounds Sterling":    (1850.7066, 0.6753),
    "Us Dollar":          (1370.3862, 0.5000),
    "Waua":               (1879.4750, 0.6858),
    "Uae Dirham":         (373.0769,  0.1361),
}

_HISTORY_START = date(2024, 1, 1)

FIELDNAMES = [
    "currency_code",
    "currency",
    "rate_date",
    "buying_rate",
    "central_rate",
    "selling_rate",
    "is_forward_filled",
    "snapshot_date",
]


# ---------------------------------------------------------------------------
# Synthetic rate generation
# ---------------------------------------------------------------------------

def fetch_all_records() -> list[dict]:
    """
    Generate a synthetic CBN exchange rate history — no network calls required.

    Each weekday gets its own date-seeded RNG so the same date always yields
    identical rates (idempotent) but adjacent days differ by up to ±0.8% per
    currency.  Weekends are omitted so extract_for_date's forward-fill logic
    triggers naturally for Saturday/Sunday requests.
    """
    end_date = date.today() + timedelta(days=30)
    records: list[dict] = []
    record_id = 1
    current = _HISTORY_START

    while current <= end_date:
        if current.weekday() < 5:  # Mon–Fri only
            rng = random.Random(int(current.strftime("%Y%m%d")))
            date_str = current.isoformat()
            for cbn_name, (base_central, base_spread) in _BASE_RATES.items():
                mult = 1.0 + rng.uniform(-0.008, 0.008)
                central = round(base_central * mult, 4)
                spread = round(base_spread * mult, 4)
                records.append({
                    "id":          record_id,
                    "ratedate":    date_str,
                    "currency":    cbn_name,
                    "buyingrate":  round(central - spread, 4),
                    "centralrate": central,
                    "sellingrate": round(central + spread, 4),
                })
                record_id += 1
        current += timedelta(days=1)

    return records


def extract_for_date(all_records: list[dict], snapshot_date: date) -> tuple[list[dict], bool]:
    """
    From the full history, return the rates published on or most recently before
    snapshot_date.  If the most recent publication is before snapshot_date
    (weekend / public holiday), rows are marked forward_filled=True.
    """
    if not all_records:
        return [], False

    cutoff = snapshot_date.isoformat()
    eligible_dates = [r["ratedate"] for r in all_records if r["ratedate"] <= cutoff]
    if not eligible_dates:
        return [], False

    rate_date = max(eligible_dates)
    forward_filled = rate_date < cutoff

    seen: set[str] = set()
    rows = []
    for r in sorted(all_records, key=lambda x: x.get("id", 0)):
        if r["ratedate"] != rate_date:
            continue
        cbn_name = r["currency"].strip().title()
        if cbn_name in seen:
            continue
        seen.add(cbn_name)
        code = CBN_CURRENCY_MAP.get(cbn_name)
        if not code:
            print(f"  ! Unmapped currency '{cbn_name}' - storing with raw name", flush=True)
            code = cbn_name[:3].upper()
        rows.append({
            "currency_code":     code,
            "currency":          cbn_name,
            "rate_date":         r["ratedate"],
            "buying_rate":       r["buyingrate"],
            "central_rate":      r["centralrate"],
            "selling_rate":      r["sellingrate"],
            "is_forward_filled": forward_filled,
            "snapshot_date":     snapshot_date.isoformat(),
        })
    return rows, forward_filled


def fetch_rates(snapshot_date: date) -> tuple[list[dict], bool]:
    """Convenience wrapper: fetch history then extract for one date."""
    return extract_for_date(fetch_all_records(), snapshot_date)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], snapshot_date: date, output_dir: Path = Path(".")) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"cbn_fx_rates_{snapshot_date}.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return out.resolve()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def ingest(
    snapshot_date: date,
    output_dir: Path = Path("."),
    dry_run: bool = False,
) -> None:
    print(f"Generating CBN rates for {snapshot_date}...")
    rows, forward_filled = fetch_rates(snapshot_date)

    if not rows:
        print("  No rates available for this date.")
        return

    label = "forward-filled from " + rows[0]["rate_date"] if forward_filled else "published"
    print(f"  {len(rows)} currencies ({label})")

    if dry_run:
        print()
        header = (
            f"{'Code':<5} {'Currency':<22} {'Rate Date':<12}"
            f" {'Buying':>12} {'Central':>12} {'Selling':>12}  FF"
        )
        print(header)
        print("-" * len(header))
        for r in rows:
            print(
                f"{r['currency_code']:<5} {r['currency']:<22} {r['rate_date']:<12}"
                f" {float(r['buying_rate']):>12.4f}"
                f" {float(r['central_rate']):>12.4f}"
                f" {float(r['selling_rate']):>12.4f}"
                f"  {'Y' if r['is_forward_filled'] else 'N'}"
            )
        return

    csv_path = write_csv(rows, snapshot_date, output_dir)
    print(f"✓ Written to {csv_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CBN official NGN exchange rates → CSV")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        metavar="YYYY-MM-DD",
        help="Snapshot date (default: today)",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        metavar="DIR",
        help="Directory to write the CSV file (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rates to stdout, write no files",
    )
    args = parser.parse_args()

    ingest(
        date.fromisoformat(args.date),
        output_dir=Path(args.output_dir),
        dry_run=args.dry_run,
    )
