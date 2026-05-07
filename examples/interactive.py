"""
Interactive kroft simulation — drive your data generation from the command line.

Usage:
    uv run examples/interactive.py
"""

import sys

from dotenv import load_dotenv

from kroft import (
    BatchGenerator,
    EvolutionController,
    MutationEngine,
    SchemaManager,
)
from shared.columns import ORDERS_COLUMNS
from shared.db import get_connection

load_dotenv()

MENU = """
┌─────────────────────────────────┐
│         kroft interactive       │
├─────────────────────────────────┤
│  [i]  Insert a batch            │
│  [u]  Update records            │
│  [d]  Delete records            │
│  [e]  Evolve schema             │
│  [s]  Show stats                │
│  [q]  Quit                      │
└─────────────────────────────────┘
"""


def prompt_int(msg: str, default: int) -> int:
    raw = input(f"{msg} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"  Invalid input, using {default}.")
        return default


def prompt_float(msg: str, default: float) -> float:
    raw = input(f"{msg} [{default}]: ").strip()
    if not raw:
        return default
    try:
        val = float(raw)
        if not 0.0 <= val <= 1.0:
            raise ValueError
        return val
    except ValueError:
        print(f"  Invalid input, using {default}.")
        return default


def show_stats(engine: MutationEngine, controller: EvolutionController):
    counters = engine.get_counters()
    summary = controller.summary()
    print("\n── Stats ──────────────────────────────")
    print(f"  Inserts : {counters['total_inserts']}")
    print(f"  Updates : {counters['total_updates']}")
    print(f"  Deletes : {counters['total_deletes']}")
    print(f"  Schema  : v{summary['schema_version']}  "
          f"(+{summary['adds']} cols added, -{summary['drops']} dropped)")
    if summary["evolution_log"]:
        print("  Evolution log:")
        for entry in summary["evolution_log"]:
            print(f"    {entry['version']} {entry['action']} → {entry['column']}")
    print("───────────────────────────────────────\n")


def main():
    print("\nWelcome to the kroft interactive simulation.")
    print("Connecting to PostgreSQL...")

    try:
        conn = get_connection()
    except Exception as e:
        print(f"  Failed to connect: {e}")
        sys.exit(1)

    table = input("Table name [orders]: ").strip() or "orders"
    batch_size = prompt_int("Default batch size", 100)

    manager = SchemaManager(conn, "public", table, ORDERS_COLUMNS)
    reset = input("Reset table? (drop + recreate) [y/N]: ").strip().lower()
    if reset == "y":
        manager.drop_table()
    manager.create_table()

    generator = BatchGenerator(schema=manager.get_active_columns())
    engine = MutationEngine(
        conn=conn,
        schema="public",
        table_name=table,
        primary_key="id",
        update_column="updated_at",
        generator=generator,
    )
    controller = EvolutionController(
        manager=manager,
        evolution_interval=1,
        evolution_probability=1.0,
        add_probability=0.7,
        max_additions=3,
        max_drops=2,
    )

    last_ids: list[str] = []
    batch_num = 0

    print(f"\nReady. Table '{table}' is set up with {len(manager.get_active_columns())} columns.\n")

    while True:
        print(MENU)
        choice = input("Action: ").strip().lower()

        if choice == "q":
            print("\nFinal stats:")
            show_stats(engine, controller)
            print("Goodbye.")
            conn.close()
            break

        elif choice == "i":
            size = prompt_int("Batch size", batch_size)
            generator.schema = manager.get_active_columns()
            rows = generator.generate_batch(batch_size=size)
            last_ids = engine.insert_batch(rows)
            batch_num += 1
            print(f"  ✓ Inserted {len(last_ids)} records.")

        elif choice == "u":
            if not last_ids:
                print("  No records inserted yet — run [i] first.")
                continue
            fraction = prompt_float("Fraction of last batch to update (0.0–1.0)", 0.2)
            updated = engine.update_batch(last_ids, fraction=fraction, probability=1.0)
            print(f"  ✓ Updated {updated} records.")

        elif choice == "d":
            if not last_ids:
                print("  No records inserted yet — run [i] first.")
                continue
            fraction = prompt_float("Fraction of last batch to delete (0.0–1.0)", 0.1)
            deleted = engine.delete_batch(last_ids, fraction=fraction, probability=1.0)
            print(f"  ✓ Deleted {deleted} records.")

        elif choice == "e":
            result = controller.evolve(batch_num or 1)
            if result:
                print(f"  ✓ {result}")
                generator.schema = manager.get_active_columns()
            else:
                print("  No evolution occurred (limits reached or probability not met).")

        elif choice == "s":
            show_stats(engine, controller)

        else:
            print("  Unknown action — choose from the menu.")


if __name__ == "__main__":
    main()
