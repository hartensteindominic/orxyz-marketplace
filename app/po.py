"""PO ledger for ORXYZ Marketplace orders.

Lifecycle:
PENDING -> FUNDS_CLEARED -> PO_SENT -> SHIPPED -> DELIVERED -> RELEASED
                                                \-> FROZEN / REFUNDED

The schema keeps Stripe Checkout Session, PaymentIntent, and Charge IDs
separate so supplier transfers can use the correct source transaction and
webhooks can reconcile without guessing.
"""
import sqlite3
import time
import uuid
from enum import Enum
from typing import Any

from .config import settings


class POState(str, Enum):
    PENDING = "pending"
    FUNDS_CLEARED = "funds_cleared"
    PO_SENT = "po_sent"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RELEASED = "released"
    FROZEN = "frozen"
    REFUNDED = "refunded"


SCHEMA = """
CREATE TABLE IF NOT EXISTS purchase_orders (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    state TEXT NOT NULL,
    buyer_email TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    supplier_total_usd REAL NOT NULL,
    list_price_usd REAL NOT NULL,
    spread_usd REAL NOT NULL,
    stripe_session_id TEXT,
    stripe_payment_intent_id TEXT,
    stripe_charge_id TEXT,
    stripe_transfer_id TEXT,
    tracking_number TEXT,
    dispute_open INTEGER NOT NULL DEFAULT 0,
    manual_approved INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);
"""

MIGRATIONS = {
    "quote_id": "ALTER TABLE purchase_orders ADD COLUMN quote_id TEXT NOT NULL DEFAULT ''",
    "stripe_session_id": "ALTER TABLE purchase_orders ADD COLUMN stripe_session_id TEXT",
    "stripe_payment_intent_id": "ALTER TABLE purchase_orders ADD COLUMN stripe_payment_intent_id TEXT",
    "stripe_charge_id": "ALTER TABLE purchase_orders ADD COLUMN stripe_charge_id TEXT",
}

ALLOWED_UPDATE_FIELDS = {
    "quote_id",
    "stripe_session_id",
    "stripe_payment_intent_id",
    "stripe_charge_id",
    "stripe_transfer_id",
    "tracking_number",
    "dispute_open",
    "manual_approved",
    "notes",
}


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.execute(SCHEMA)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(purchase_orders)").fetchall()}
    for name, ddl in MIGRATIONS.items():
        if name not in columns:
            conn.execute(ddl)
    return conn


def create_po(*, quote_id: str, buyer_email: str, supplier_id: str,
              supplier_total_usd: float, list_price_usd: float) -> str:
    po_id = f"PO-{uuid.uuid4().hex[:10].upper()}"
    now = time.time()
    with _db() as conn:
        conn.execute(
            """INSERT INTO purchase_orders
               (id, quote_id, created_at, updated_at, state, buyer_email,
                supplier_id, supplier_total_usd, list_price_usd, spread_usd,
                dispute_open, manual_approved)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (po_id, quote_id, now, now, POState.PENDING.value, buyer_email,
             supplier_id, supplier_total_usd, list_price_usd,
             round(list_price_usd - supplier_total_usd, 2), 0, 0),
        )
    return po_id


def get_po(po_id: str) -> dict | None:
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM purchase_orders WHERE id=?", (po_id,)).fetchone()
        return dict(row) if row else None


def get_po_by_session(session_id: str) -> dict | None:
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE stripe_session_id=? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None


def get_po_by_payment_intent(payment_intent_id: str) -> dict | None:
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE stripe_payment_intent_id=? ORDER BY created_at DESC LIMIT 1",
            (payment_intent_id,),
        ).fetchone()
        return dict(row) if row else None


def get_po_by_charge(charge_id: str) -> dict | None:
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE stripe_charge_id=? ORDER BY created_at DESC LIMIT 1",
            (charge_id,),
        ).fetchone()
        return dict(row) if row else None


def set_state(po_id: str, state: POState, **fields: Any) -> None:
    unknown = set(fields) - ALLOWED_UPDATE_FIELDS
    if unknown:
        raise ValueError(f"unsupported PO fields: {sorted(unknown)}")
    sets = ["state=?", "updated_at=?"]
    vals: list[Any] = [state.value, time.time()]
    for key, value in fields.items():
        sets.append(f"{key}=?")
        vals.append(value)
    vals.append(po_id)
    with _db() as conn:
        conn.execute(f"UPDATE purchase_orders SET {', '.join(sets)} WHERE id=?", vals)


def update_po(po_id: str, **fields: Any) -> None:
    po = get_po(po_id)
    if not po:
        raise ValueError("unknown PO")
    set_state(po_id, POState(po["state"]), **fields)


def list_pos(state: POState | None = None) -> list[dict]:
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        if state:
            rows = conn.execute(
                "SELECT * FROM purchase_orders WHERE state=? ORDER BY created_at DESC",
                (state.value,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM purchase_orders ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]
