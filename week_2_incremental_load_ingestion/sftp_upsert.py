"""
Demo 2 - Incremental Load via SFTP Upsert (ClearWatch Watchlist)

ClearWatch drops a complete watchlist snapshot to the SFTP server every morning.
The file is always a full dump - it does not tell you what changed.

Strategy: upsert on vendor_entity_id.
  - Entity not in table  →  INSERT
  - Entity already there →  UPDATE with latest values

The table reflects current watchlist state. Run it twice for the same file
and the second run is a no-op (values written are identical to what is there).

Setup (one-time):
    # Simulate the vendor delivering Monday's file to SFTP
    uv run shared/clearwatch/simulate_vendor_day.py --date 2021-01-04

    # Then Tuesday's file (some entities will have changed status or risk)
    uv run shared/clearwatch/simulate_vendor_day.py --date 2021-01-05

Usage:
    uv run week_2_incremental_load_ingestion/sftp_upsert.py

Reset between full demos:
    psql -c "DROP TABLE IF EXISTS clearwatch_watchlist;"
"""

import csv
import io
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")
sys.path.insert(0, str(Path(__file__).parents[1]))
from shared.db import get_connection

# ---------------------------------------------------------------------------
# SFTP config
# ---------------------------------------------------------------------------

SFTP_HOST       = os.getenv("SFTP_HOST", "localhost")
SFTP_PORT       = int(os.getenv("SFTP_PORT", "2222"))
SFTP_USER       = os.getenv("SFTP_USER", "naijapaveclearwatchdata")
SFTP_PASS       = os.getenv("SFTP_PASS", "pass")
SFTP_REMOTE_DIR = os.getenv("SFTP_REMOTE_DIR", "upload")

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

# TODO 1: Write the CREATE TABLE statement.
#   Primary key is vendor_entity_id - this is what the upsert keys on.
CREATE = """
CREATE TABLE IF NOT EXISTS clearwatch_watchlist (
    vendor_entity_id    TEXT PRIMARY KEY,
    entity_name         TEXT,
    entity_type         TEXT,
    aliases             TEXT,
    country             TEXT,
    date_of_birth       TEXT,
    registration_number TEXT,
    watchlist_type      TEXT,
    risk_category       TEXT,
    status              TEXT,
    list_source         TEXT,
    listed_date         DATE,
    last_reviewed_date  DATE,
    file_generated_at   TIMESTAMPTZ,
    loaded_at           TIMESTAMPTZ DEFAULT NOW()
)
"""

# TODO 2: Write the UPSERT statement.
#   On conflict (same vendor_entity_id), overwrite mutable fields.
#   We do NOT update listed_date - that is when they first appeared.
UPSERT = """
INSERT INTO clearwatch_watchlist (
    vendor_entity_id, entity_name, entity_type, aliases, country,
    date_of_birth, registration_number, watchlist_type, risk_category,
    status, list_source, listed_date, last_reviewed_date, file_generated_at
) VALUES (
    %(vendor_entity_id)s, %(entity_name)s, %(entity_type)s, %(aliases)s,
    %(country)s, %(date_of_birth)s, %(registration_number)s,
    %(watchlist_type)s, %(risk_category)s, %(status)s, %(list_source)s,
    %(listed_date)s, %(last_reviewed_date)s, %(file_generated_at)s
)
ON CONFLICT (vendor_entity_id) DO UPDATE SET
    entity_name         = EXCLUDED.entity_name,
    aliases             = EXCLUDED.aliases,
    risk_category       = EXCLUDED.risk_category,
    status              = EXCLUDED.status,
    last_reviewed_date  = EXCLUDED.last_reviewed_date,
    file_generated_at   = EXCLUDED.file_generated_at,
    loaded_at           = NOW()
"""


# ---------------------------------------------------------------------------
# SFTP download
# ---------------------------------------------------------------------------

def download_latest(sftp) -> tuple[str, str]:
    """Return (filename, csv_content) for the most recent watchlist file."""
    files = [
        f for f in sftp.listdir(SFTP_REMOTE_DIR)
        if f.startswith("clearwatch_watchlist_") and f.endswith(".csv")
    ]
    if not files:
        raise FileNotFoundError(f"No watchlist file found in {SFTP_REMOTE_DIR}/")

    filename = sorted(files)[-1]
    remote_path = f"{SFTP_REMOTE_DIR}/{filename}"

    buf = io.BytesIO()
    sftp.getfo(remote_path, buf)
    return filename, buf.getvalue().decode("utf-8")


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def coerce(row: dict) -> dict:
    row["listed_date"]        = row["listed_date"] or None
    row["last_reviewed_date"] = row["last_reviewed_date"] or None
    row["date_of_birth"]      = row["date_of_birth"] or None
    row["file_generated_at"]  = row["file_generated_at"] or None
    return row


def load() -> None:
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        filename, content = download_latest(sftp)
    finally:
        sftp.close()
        transport.close()

    print(f"Downloaded {filename}")

    rows = [coerce(row) for row in csv.DictReader(io.StringIO(content))]
    if not rows:
        print("File is empty - nothing to do")
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE)
            cur.executemany(UPSERT, rows)
        conn.commit()
    finally:
        conn.close()

    print(f"Upserted {len(rows)} rows from {filename}")


if __name__ == "__main__":
    load()
