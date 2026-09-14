"""PO ledger: sqlite-backed record of every marketplace order.

States: PENDING -> FUNDS_CLEARED -> PO_SENT -> SHIPPED -> DELIVERED ->
         RELEASED | FROZEN | REFUNDED
"""
import sqlite3
import time
import uuid
from enum import Enum

from .config import settings


class POState(str, Enum):
    PENDING = "pending"            # checkout created, awaiting payment
    FUNDS_CLEARED = "funds_cleared"
    PO_SENT = "po_sent"
    SHIPPED = "shipped"            # tracking number on file
    DELIVERED = "delivered"
    RELEASED = "released"          # supplier paid
    FROZEN = "frozen"              # dispute: do not release
    REFUNDED = "refunded"


SCHEMA = """
CREATE TABLE IF NOT EXISTS purchase_orders (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    state TEXT NOT NULL,
    buyer_email TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    supplier_total_usd REAL NOT NULL,
    list_price_usd REAL NOT NULL,
    spread_usd REAL NOT NULL,
    stripe_payment_intent TEXT,
    stripe_transfer_id TEXT,
    tracking_number TEXT,
    dispute_open INTEGER NOT NULL DEFAULT 0,
    manual_approved INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);
"""


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.execute(SCHEMA)
    return conn


def create_po(*, buyer_email: str, supplier_id: str, supplier_total_usd: float,
              list_price_usd: float, stripe_payment_intent: str | None = None) -> str:
    po_id = f"PO-{uuid.uuid4().hex[:10].upper()}"
    now = time.time()
    with _db() as conn:
        conn.execute(
            """INSERT INTO purchase_orders
               (id, created_at, updated_at, state, buyer_email, supplier_id,
                supplier_total_usd, list_price_usd, spread_usd,
                stripe_payment_intent, dispute_open, manual_approved)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (po_id, now, now, POState.PENDING.value, buyer_email, supplier_id,
             supplier_total_usd, list_price_usd,
             round(list_price_usd - supplier_total_usd, 2),
             stripe_payment_intent, 0, 0),
        )
    return po_id


def get_po(po_id: str) -> dict | None:
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM purchase_orders WHERE id=?", (po_id,)).fetchone()
        return dict(row) if row else None


def set_state(po_id: str, state: POState, **fields) -> None:
    sets = ["state=?", "updated_at=?"]
    vals: list = [state.value, time.time()]
    for k, v in fields.items():
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(po_id)
    with _db() as conn:
        conn.execute(f"UPDATE purchase_orders SET {', '.join(sets)} WHERE id=?", vals)


def list_pos(state: POState | None = None) -> list[dict]:
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        if state:
            rows = conn.execute(
                "SELECT * FROM purchase_orders WHERE state=? ORDER BY created_at DESC",
                (state.value,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM purchase_orders ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
