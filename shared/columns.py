import random
import uuid
from datetime import datetime, timezone

from kroft import ColumnDefinition

# A reusable column pool for use across chapters.
# Reserved columns are excluded from the initial schema
# and can be promoted later via EvolutionController.

ORDERS_COLUMNS = {
    "id": ColumnDefinition(
        "id", "UUID", lambda: str(uuid.uuid4()), constraints="PRIMARY KEY"
    ),
    "created_at": ColumnDefinition(
        "created_at", "TIMESTAMP",
        lambda: datetime.now(timezone.utc).isoformat(),
        protected=True,
    ),
    "updated_at": ColumnDefinition(
        "updated_at", "TIMESTAMP",
        lambda: datetime.now(timezone.utc).isoformat(),
        protected=True,
    ),
    "customer_id": ColumnDefinition(
        "customer_id", "UUID", lambda: str(uuid.uuid4())
    ),
    "product": ColumnDefinition(
        "product", "TEXT",
        lambda: random.choice(["laptop", "phone", "tablet", "headphones", "keyboard"]),
    ),
    "quantity": ColumnDefinition(
        "quantity", "INT", lambda: random.randint(1, 10)
    ),
    "unit_price": ColumnDefinition(
        "unit_price", "FLOAT", lambda: round(random.uniform(10.0, 1000.0), 2)
    ),
    "status": ColumnDefinition(
        "status", "TEXT",
        lambda: random.choice(["pending", "confirmed", "shipped", "delivered"]),
    ),
    # Reserved — available for schema evolution chapters
    "discount_pct": ColumnDefinition(
        "discount_pct", "FLOAT", lambda: 0.0, reserved=True
    ),
    "region": ColumnDefinition(
        "region", "TEXT",
        lambda: random.choice(["NA", "EU", "APAC"]),
        reserved=True,
    ),
    "return_requested": ColumnDefinition(
        "return_requested", "BOOLEAN", lambda: False, reserved=True
    ),
}
