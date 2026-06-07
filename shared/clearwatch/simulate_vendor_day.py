"""
Simulates a ClearWatch vendor daily file delivery.

Generates a deterministic watchlist CSV snapshot for the given date (seeded
by date so the same date always produces the same file) and uploads it to
the SFTP server defined in the environment.

Usage:
    python simulate_vendor_day.py --date 2021-01-05
    python simulate_vendor_day.py --date 2021-01-05 --records 50
    python simulate_vendor_day.py --date 2021-01-05 --dry-run
"""

import argparse
import csv
import io
import os
import random
import tempfile
from datetime import date, timedelta
from pathlib import Path

import paramiko
from dotenv import load_dotenv
from faker import Faker
from mimesis import Person as MimesisPerson
from mimesis.locales import Locale

load_dotenv(Path(__file__).parents[2] / ".env")

# ---------------------------------------------------------------------------
# SFTP config (override via .env or environment variables)
# ---------------------------------------------------------------------------

SFTP_HOST = os.getenv("SFTP_HOST", "localhost")
SFTP_PORT = int(os.getenv("SFTP_PORT", "2222"))
SFTP_USER = os.getenv("SFTP_USER", "naijapaveclearwatchdata")
SFTP_PASS = os.getenv("SFTP_PASS", "pass")
SFTP_REMOTE_DIR = os.getenv("SFTP_REMOTE_DIR", "upload")

# ---------------------------------------------------------------------------
# Watchlist domain constants
# ---------------------------------------------------------------------------

WATCHLIST_TYPES = ["SANCTIONS", "ADVERSE_MEDIA", "PEP", "HIGH_RISK_ENTITY"]
RISK_CATEGORIES = ["HIGH", "MEDIUM", "LOW"]
STATUSES = ["ACTIVE", "INACTIVE"]
ENTITY_TYPES = ["PERSON", "COMPANY"]

LIST_SOURCE_MAP = {
    "SANCTIONS":        "CLEARWATCH_SANCTIONS",
    "ADVERSE_MEDIA":    "CLEARWATCH_ADVERSE_MEDIA",
    "PEP":              "CLEARWATCH_PEP",
    "HIGH_RISK_ENTITY": "CLEARWATCH_HIGH_RISK",
}

RISK_WEIGHT = {
    "SANCTIONS":        ("HIGH",   0.8),
    "ADVERSE_MEDIA":    ("MEDIUM", 0.6),
    "PEP":              ("MEDIUM", 0.6),
    "HIGH_RISK_ENTITY": ("HIGH",   0.75),
}

COUNTRY_POOL = ["NG", "NG", "NG", "NG", "GH", "NE", "CM", "SN", "ZA"]

FIELDNAMES = [
    "vendor_entity_id",
    "entity_name",
    "entity_type",
    "aliases",
    "country",
    "date_of_birth",
    "registration_number",
    "watchlist_type",
    "risk_category",
    "status",
    "list_source",
    "listed_date",
    "last_reviewed_date",
    "file_generated_at",
]

# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def _risk(watchlist: str, rng: random.Random) -> str:
    primary, primary_prob = RISK_WEIGHT[watchlist]
    if rng.random() < primary_prob:
        return primary
    fallback = [r for r in RISK_CATEGORIES if r != primary]
    return rng.choice(fallback)


def _aliases(name: str, rng: random.Random) -> str:
    parts = name.split()
    options = [f"{parts[0][0]}. {parts[-1]}"] if len(parts) >= 2 else []
    if rng.random() > 0.4 and len(parts) >= 2:
        options.append(f"{parts[0]} {parts[-1][0]}.")
    return "|".join(options) if options else ""


def _random_past_date(rng: random.Random, earliest: date, latest: date) -> str:
    delta = (latest - earliest).days
    return (earliest + timedelta(days=rng.randint(0, max(delta, 0)))).isoformat()


def generate_csv(run_date: date, n_records: int = 50) -> str:
    # Seed both faker and the stdlib rng from the date so the output is
    # reproducible: the same --date always produces the same file.
    seed = int(run_date.strftime("%Y%m%d"))
    Faker.seed(seed)
    fake = Faker(["en_NG", "en_GB"])
    mp = MimesisPerson(Locale.EN, seed=seed)
    rng = random.Random(seed)

    file_generated_at = f"{run_date} 09:00:00"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()

    earliest_listing = date(2015, 1, 1)

    for i in range(1, n_records + 1):
        entity_type = rng.choice(ENTITY_TYPES)
        watchlist = rng.choice(WATCHLIST_TYPES)
        risk = _risk(watchlist, rng)
        status = rng.choices(STATUSES, weights=[0.8, 0.2])[0]
        country = rng.choice(COUNTRY_POOL)
        listed = date.fromisoformat(
            _random_past_date(rng, earliest_listing, run_date - timedelta(days=30))
        )
        last_reviewed = run_date - timedelta(days=rng.randint(0, 14))
        last_reviewed = max(last_reviewed, listed)

        if entity_type == "PERSON":
            name = f"{fake.first_name()} {mp.last_name()}"
            dob = fake.date_of_birth(minimum_age=25, maximum_age=75).isoformat()
            reg = ""
            aliases = _aliases(name, rng)
        else:
            name = f"{fake.word().title()} {fake.word().title()} Ltd-{i:03d}"
            dob = ""
            reg = f"RC{rng.randint(100000, 999999)}"
            aliases = f"{fake.word().title()} {fake.word().title()}|{fake.word().title()} Ltd"

        writer.writerow({
            "vendor_entity_id":    f"CW-{i:06d}",
            "entity_name":         name,
            "entity_type":         entity_type,
            "aliases":             aliases,
            "country":             country,
            "date_of_birth":       dob,
            "registration_number": reg,
            "watchlist_type":      watchlist,
            "risk_category":       risk,
            "status":              status,
            "list_source":         LIST_SOURCE_MAP[watchlist],
            "listed_date":         listed.isoformat(),
            "last_reviewed_date":  last_reviewed.isoformat(),
            "file_generated_at":   file_generated_at,
        })

    return buf.getvalue()


# ---------------------------------------------------------------------------
# SFTP upload
# ---------------------------------------------------------------------------

def upload_via_sftp(content: str, filename: str, no_overwrite: bool = False) -> None:
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)

    try:
        try:
            sftp.stat(SFTP_REMOTE_DIR)
        except FileNotFoundError:
            sftp.mkdir(SFTP_REMOTE_DIR)

        # Find any existing watchlist files from previous runs
        existing = [
            f.filename
            for f in sftp.listdir_attr(SFTP_REMOTE_DIR)
            if f.filename.startswith("clearwatch_watchlist_") and f.filename.endswith(".csv")
        ]

        if no_overwrite and existing:
            print(
                f"⚠ Skipped - {len(existing)} file(s) already present "
                f"({existing[0]}{'...' if len(existing) > 1 else ''}). "
                f"Remove --no-overwrite to replace."
            )
            return

        # Remove stale files before uploading the new one
        for old_file in existing:
            sftp.remove(f"{SFTP_REMOTE_DIR}/{old_file}")
            print(f"  Removed {old_file}")

        remote_path = f"{SFTP_REMOTE_DIR}/{filename}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            sftp.put(tmp_path, remote_path)
        finally:
            os.unlink(tmp_path)

        print(f"✓ Uploaded → sftp://{SFTP_HOST}:{SFTP_PORT}/{remote_path}")
    finally:
        sftp.close()
        transport.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate and deliver a ClearWatch watchlist file via SFTP"
    )
    parser.add_argument(
        "--date",
        required=True,
        metavar="YYYY-MM-DD",
        help="Run date - controls file_generated_at and seeds data generation",
    )
    parser.add_argument(
        "--records",
        type=int,
        default=50,
        metavar="N",
        help="Number of watchlist records to generate (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the CSV to stdout without uploading",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Skip the upload if a file for this date already exists on the server",
    )
    args = parser.parse_args()

    run_date = date.fromisoformat(args.date)
    filename = f"clearwatch_watchlist_{run_date}.csv"
    content = generate_csv(run_date, n_records=args.records)

    print(f"Generated {filename}  ({args.records} records)")

    if args.dry_run:
        print()
        print(content)
    else:
        upload_via_sftp(content, filename, no_overwrite=args.no_overwrite)
