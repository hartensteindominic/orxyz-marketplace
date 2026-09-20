"""Bandwidth settlement ledger for ORXYZ.

This module does not meter traffic itself. A vetted bandwidth provider must
measure billable traffic and revenue. ORXYZ only credits rewards after a
provider-confirmed settlement event reaches the server-side ingestion route.
"""
from __future__ import annotations

import sqlite3
import time
from decimal import Decimal, ROUND_DOWN
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import settings

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS bandwidth_wallets (
    user_id TEXT PRIMARY KEY,
    spendable_orxyz REAL NOT NULL DEFAULT 0,
    lifetime_orxyz REAL NOT NULL DEFAULT 0,
    verified_gb REAL NOT NULL DEFAULT 0,
    provider_revenue_usd REAL NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS bandwidth_settlements (
    provider_event_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    user_id TEXT NOT NULL,
    verified_gb REAL NOT NULL,
    provider_revenue_usd REAL NOT NULL,
    reward_share REAL NOT NULL,
    reward_orxyz REAL NOT NULL,
    created_at REAL NOT NULL
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS bandwidth_wallets (
    user_id TEXT PRIMARY KEY,
    spendable_orxyz DOUBLE PRECISION NOT NULL DEFAULT 0,
    lifetime_orxyz DOUBLE PRECISION NOT NULL DEFAULT 0,
    verified_gb DOUBLE PRECISION NOT NULL DEFAULT 0,
    provider_revenue_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
    updated_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS bandwidth_settlements (
    provider_event_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    user_id TEXT NOT NULL,
    verified_gb DOUBLE PRECISION NOT NULL,
    provider_revenue_usd DOUBLE PRECISION NOT NULL,
    reward_share DOUBLE PRECISION NOT NULL,
    reward_orxyz DOUBLE PRECISION NOT NULL,
    created_at DOUBLE PRECISION NOT NULL
);
"""


def _use_postgres() -> bool:
    return settings.durable_database_configured


def _postgres_dsn() -> str:
    url = settings.database_url
    if url.lower().startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _sql(query: str) -> str:
    return query.replace("?", "%s") if _use_postgres() else query


def _db():
    if _use_postgres():
        conn = psycopg.connect(_postgres_dsn(), row_factory=dict_row)
        for stmt in POSTGRES_SCHEMA.strip().split(";"):
            if stmt.strip():
                conn.execute(stmt)
        conn.commit()
        return conn

    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SQLITE_SCHEMA)
    conn.commit()
    return conn


def _q(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_DOWN))


def credit_verified_bandwidth(
    *,
    provider_event_id: str,
    provider: str,
    user_id: str,
    verified_gb: float,
    provider_revenue_usd: float,
    reward_share: float,
) -> dict[str, Any]:
    event_id = provider_event_id.strip()
    provider_name = provider.strip().lower()
    user = user_id.strip()

    if not event_id or len(event_id) > 180:
        raise ValueError("invalid provider event id")
    if not provider_name or len(provider_name) > 80:
        raise ValueError("invalid provider")
    if not user or len(user) > 180:
        raise ValueError("invalid user id")
    if verified_gb < 0 or provider_revenue_usd < 0:
        raise ValueError("usage and revenue must be non-negative")
    if not 0 <= reward_share <= 0.25:
        raise ValueError("reward share must be between 0 and 25%")

    reward = _q(provider_revenue_usd * reward_share)
    now = time.time()

    with _db() as conn:
        existing = conn.execute(
            _sql("SELECT * FROM bandwidth_settlements WHERE provider_event_id=?"),
            (event_id,),
        ).fetchone()
        if existing:
            row = dict(existing)
            row["duplicate"] = True
            return row

        conn.execute(
            _sql(
                """INSERT INTO bandwidth_settlements
                   (provider_event_id, provider, user_id, verified_gb,
                    provider_revenue_usd, reward_share, reward_orxyz, created_at)
                   VALUES (?,?,?,?,?,?,?,?)"""
            ),
            (event_id, provider_name, user, verified_gb, provider_revenue_usd,
             reward_share, reward, now),
        )

        wallet = conn.execute(
            _sql("SELECT * FROM bandwidth_wallets WHERE user_id=?"),
            (user,),
        ).fetchone()
        if wallet:
            conn.execute(
                _sql(
                    """UPDATE bandwidth_wallets
                       SET spendable_orxyz=spendable_orxyz+?,
                           lifetime_orxyz=lifetime_orxyz+?,
                           verified_gb=verified_gb+?,
                           provider_revenue_usd=provider_revenue_usd+?,
                           updated_at=?
                       WHERE user_id=?"""
                ),
                (reward, reward, verified_gb, provider_revenue_usd, now, user),
            )
        else:
            conn.execute(
                _sql(
                    """INSERT INTO bandwidth_wallets
                       (user_id, spendable_orxyz, lifetime_orxyz, verified_gb,
                        provider_revenue_usd, updated_at)
                       VALUES (?,?,?,?,?,?)"""
                ),
                (user, reward, reward, verified_gb, provider_revenue_usd, now),
            )

    return {
        "provider_event_id": event_id,
        "provider": provider_name,
        "user_id": user,
        "verified_gb": verified_gb,
        "provider_revenue_usd": provider_revenue_usd,
        "reward_share": reward_share,
        "reward_orxyz": reward,
        "duplicate": False,
    }


def get_bandwidth_wallet(user_id: str) -> dict[str, Any] | None:
    with _db() as conn:
        row = conn.execute(
            _sql("SELECT * FROM bandwidth_wallets WHERE user_id=?"),
            (user_id.strip(),),
        ).fetchone()
        return dict(row) if row else None


def list_bandwidth_settlements(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    with _db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bandwidth_settlements ORDER BY created_at DESC LIMIT {safe_limit}"
        ).fetchall()
        return [dict(row) for row in rows]
