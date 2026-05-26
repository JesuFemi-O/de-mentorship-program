"""
Provision Metabase: admin user, database connection, questions, and dashboard.
Idempotent — safe to run multiple times.

Usage:
    python infrastructure/metabase/setup.py
"""

import os
import sys
import time

import requests

METABASE_URL = os.getenv("METABASE_URL", "http://localhost:3000")
ADMIN_EMAIL = os.getenv("METABASE_EMAIL", "admin@cdcraft.local")
ADMIN_PASSWORD = os.getenv("METABASE_PASSWORD", "Cdcraft123!")
POSTGRES_HOST = "postgres"
POSTGRES_PORT = 5432
POSTGRES_DB = os.getenv("POSTGRES_DB", "cdcdemo")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

DASHBOARD_NAME = "Week 1 — Full Load Lesson"

QUESTIONS = [
    {
        "name": "Current FX Rates (NGN)",
        "query": (
            "SELECT currency_code, currency, buying_rate, central_rate, selling_rate\n"
            "FROM cbn_fx_rates\n"
            "ORDER BY central_rate DESC"
        ),
        "display": "table",
        "visualization_settings": {},
    },
    {
        "name": "USD Rate Trend Over Time",
        "query": (
            "SELECT snapshot_date, central_rate\n"
            "FROM cbn_fx_rates\n"
            "WHERE currency_code = 'USD'\n"
            "ORDER BY snapshot_date"
        ),
        "display": "line",
        "visualization_settings": {
            "graph.dimensions": ["snapshot_date"],
            "graph.metrics": ["central_rate"],
            "graph.x_axis.title_text": "Date",
            "graph.y_axis.title_text": "NGN per USD",
        },
    },
]

# Dashboard card layout: 24-col grid, two cards side by side
CARD_LAYOUT = [
    {"col": 0,  "row": 0, "size_x": 12, "size_y": 8},
    {"col": 12, "row": 0, "size_x": 12, "size_y": 8},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for_metabase(timeout: int = 180) -> None:
    print("Waiting for Metabase...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{METABASE_URL}/api/health", timeout=5)
            if r.status_code == 200 and r.json().get("status") == "ok":
                print("Metabase is ready.")
                return
        except requests.RequestException:
            pass
        time.sleep(4)
    sys.exit("ERROR: Metabase did not become ready within the timeout.")


def get_setup_token() -> str | None:
    r = requests.get(f"{METABASE_URL}/api/session/properties", timeout=10)
    r.raise_for_status()
    return r.json().get("setup-token")


def initial_setup(token: str) -> None:
    print("First-time setup: creating admin user and database connection...")
    payload = {
        "token": token,
        "user": {
            "first_name": "Admin",
            "last_name": "CDCraft",
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "site_name": "CDCraft",
        },
        "database": {
            "engine": "postgres",
            "name": POSTGRES_DB,
            "details": {
                "host": POSTGRES_HOST,
                "port": POSTGRES_PORT,
                "dbname": POSTGRES_DB,
                "user": POSTGRES_USER,
                "password": POSTGRES_PASSWORD,
                "ssl": False,
            },
            "is_full_sync": True,
            "is_on_demand": False,
        },
        "prefs": {
            "site_name": "CDCraft",
            "allow_tracking": False,
        },
    }
    r = requests.post(f"{METABASE_URL}/api/setup", json=payload, timeout=30)
    if r.status_code == 403:
        print("User already exists — skipping initial setup.")
        return
    if r.status_code not in (200, 201):
        sys.exit(f"ERROR: Setup failed {r.status_code}: {r.text}")
    print("Setup complete.")


def login() -> str:
    r = requests.post(
        f"{METABASE_URL}/api/session",
        json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        sys.exit(f"ERROR: Login failed {r.status_code}: {r.text}")
    return r.json()["id"]


def get_or_create_database(session: str) -> int:
    headers = {"X-Metabase-Session": session}
    r = requests.get(f"{METABASE_URL}/api/database", headers=headers, timeout=10)
    r.raise_for_status()
    # Response can be a list or {"data": [...]}
    databases = r.json()
    if isinstance(databases, dict):
        databases = databases.get("data", [])
    for db in databases:
        if db.get("name") == POSTGRES_DB:
            print(f"Database '{POSTGRES_DB}' already exists (id={db['id']}).")
            return db["id"]

    payload = {
        "engine": "postgres",
        "name": POSTGRES_DB,
        "details": {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "ssl": False,
        },
        "is_full_sync": True,
        "is_on_demand": False,
    }
    r = requests.post(f"{METABASE_URL}/api/database", headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    db_id = r.json()["id"]
    print(f"Created database '{POSTGRES_DB}' (id={db_id}).")
    return db_id


def get_or_create_card(session: str, db_id: int, q: dict) -> int:
    headers = {"X-Metabase-Session": session}
    r = requests.get(f"{METABASE_URL}/api/card", headers=headers, timeout=10)
    r.raise_for_status()
    for card in r.json():
        if card.get("name") == q["name"]:
            print(f"Card '{q['name']}' already exists (id={card['id']}).")
            return card["id"]

    payload = {
        "name": q["name"],
        "dataset_query": {
            "type": "native",
            "native": {"query": q["query"]},
            "database": db_id,
        },
        "display": q["display"],
        "visualization_settings": q["visualization_settings"],
    }
    r = requests.post(f"{METABASE_URL}/api/card", headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    card_id = r.json()["id"]
    print(f"Created card '{q['name']}' (id={card_id}).")
    return card_id


def add_cards_to_dashboard(session: str, dash_id: int, card_ids: list[int]) -> None:
    headers = {"X-Metabase-Session": session}
    cards_payload = [
        {
            "id": -(i + 1),  # negative ID signals a new dashcard
            "card_id": card_id,
            "col": layout["col"],
            "row": layout["row"],
            "size_x": layout["size_x"],
            "size_y": layout["size_y"],
            "series": [],
            "parameter_mappings": [],
            "visualization_settings": {},
        }
        for i, (card_id, layout) in enumerate(zip(card_ids, CARD_LAYOUT))
    ]
    r = requests.put(
        f"{METABASE_URL}/api/dashboard/{dash_id}/cards",
        headers=headers,
        json={"cards": cards_payload},
        timeout=15,
    )
    if not r.ok:
        sys.exit(f"ERROR adding cards: {r.status_code} {r.text}")
    print(f"Added {len(r.json().get('cards', []))} cards to dashboard.")


def get_or_create_dashboard(session: str, card_ids: list[int]) -> int:
    headers = {"X-Metabase-Session": session}

    r = requests.get(f"{METABASE_URL}/api/dashboard", headers=headers, timeout=10)
    r.raise_for_status()
    for dash in r.json():
        if dash.get("name") == DASHBOARD_NAME:
            dash_id = dash["id"]
            print(f"Dashboard '{DASHBOARD_NAME}' already exists (id={dash_id}).")
            # Ensure cards are attached (handles partial setup)
            detail = requests.get(
                f"{METABASE_URL}/api/dashboard/{dash_id}", headers=headers, timeout=10
            )
            detail.raise_for_status()
            if not detail.json().get("dashcards") and not detail.json().get("cards"):
                print("Dashboard has no cards — adding them now.")
                add_cards_to_dashboard(session, dash_id, card_ids)
            return dash_id

    r = requests.post(
        f"{METABASE_URL}/api/dashboard",
        headers=headers,
        json={
            "name": DASHBOARD_NAME,
            "description": (
                "Panel 1 works after any load. "
                "Panel 2 (USD trend) breaks after v1_naive_load — it needs snapshot_date, "
                "which only v2_snapshot_load adds."
            ),
        },
        timeout=15,
    )
    r.raise_for_status()
    dash_id = r.json()["id"]
    print(f"Created dashboard '{DASHBOARD_NAME}' (id={dash_id}).")
    add_cards_to_dashboard(session, dash_id, card_ids)
    return dash_id


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    wait_for_metabase()

    token = get_setup_token()
    if token:
        initial_setup(token)

    session = login()
    db_id = get_or_create_database(session)
    card_ids = [get_or_create_card(session, db_id, q) for q in QUESTIONS]
    dash_id = get_or_create_dashboard(session, card_ids)

    print(f"\nReady. Open http://localhost:3000/dashboard/{dash_id}")
    print(f"Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()
