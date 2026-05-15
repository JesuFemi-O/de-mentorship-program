"""
Fetches CBN official NGN exchange rates and writes a dated CSV.

This is a course data-preparation script - it produces the source file
students will use in the full-load lesson.  Loading into the warehouse
is the student exercise.

Weekend / public-holiday handling: CBN does not publish on those days.
The script detects this automatically - if the API's most recent publication
is before the requested date, rows are marked is_forward_filled=TRUE.

Usage:
    python ingest_cbn_fx.py                           # today
    python ingest_cbn_fx.py --date 2025-01-15         # specific date
    python ingest_cbn_fx.py --date 2025-01-15 --output-dir data/cbn
    python ingest_cbn_fx.py --dry-run                 # print, no files
"""

import argparse
import csv
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

CBN_API = "https://www.cbn.gov.ng/api/GetAllExchangeRates"

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
# API
# ---------------------------------------------------------------------------

def fetch_all_records() -> list[dict]:
    """Fetch the full CBN exchange rate history (one API call, ~60k records)."""
    resp = requests.get(
        CBN_API,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.cbn.gov.ng/rates/ExchRateByCurrency.html",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


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

    # CBN occasionally publishes duplicate rows for the same currency on the same
    # date (e.g. CFA appears twice on 2026-05-04, second entry is a paste error).
    # Keep the first occurrence (lowest id) to preserve the correct value.
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
    print(f"Fetching CBN rates for {snapshot_date}...")
    rows, forward_filled = fetch_rates(snapshot_date)

    if not rows:
        print("  No data returned from CBN API.")
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
