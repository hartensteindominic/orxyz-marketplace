"""Server-side approved quote registry.

Approved quotes are loaded from ORXYZ_APPROVED_QUOTES_JSON. Nothing in the
browser may supply supplier cost, list price, connected-account details, or
release mode.

Example environment value (illustrative only):
[
  {
    "id": "ORXYZ-Q-EXAMPLE",
    "buyer_email": "buyer@example.com",
    "supplier_id": "conexdepot",
    "description": "1 x 40ft high-cube open-side container",
    "supplier_total_usd": "19500.00",
    "list_price_usd": "21250.00",
    "expires_at": "2026-09-30T23:59:59Z",
    "release_mode": "controlled"
  }
]
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum

from .config import settings


MONEY = Decimal("0.01")


class ReleaseMode(str, Enum):
    CONTROLLED = "controlled"
    INSTANT = "instant"


def _money(value: object) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("invalid quote amount")
    if amount <= 0:
        raise ValueError("quote amounts must be positive")
    return amount


def _utc(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ApprovedQuote:
    id: str
    buyer_email: str
    supplier_id: str
    description: str
    supplier_total_usd: Decimal
    list_price_usd: Decimal
    expires_at: datetime
    release_mode: ReleaseMode = ReleaseMode.CONTROLLED

    @property
    def spread_usd(self) -> Decimal:
        return (self.list_price_usd - self.supplier_total_usd).quantize(MONEY)

    @property
    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


def _load_quotes() -> dict[str, ApprovedQuote]:
    raw = settings.approved_quotes_json.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ORXYZ_APPROVED_QUOTES_JSON is not valid JSON") from exc
    if not isinstance(parsed, list):
        raise RuntimeError("ORXYZ_APPROVED_QUOTES_JSON must be a JSON array")

    quotes: dict[str, ApprovedQuote] = {}
    for item in parsed:
        if not isinstance(item, dict):
            raise RuntimeError("every approved quote must be an object")
        quote_id = str(item.get("id", "")).strip().upper()
        buyer_email = str(item.get("buyer_email", "")).strip().lower()
        supplier_id = str(item.get("supplier_id", "")).strip()
        description = str(item.get("description", "")).strip()
        expires_at = str(item.get("expires_at", "")).strip()
        if not quote_id or not buyer_email or not supplier_id or not description or not expires_at:
            raise RuntimeError("approved quote is missing required fields")
        supplier_total = _money(item.get("supplier_total_usd"))
        list_price = _money(item.get("list_price_usd"))
        if list_price <= supplier_total:
            raise RuntimeError(f"{quote_id}: list price must exceed supplier cost")
        try:
            release_mode = ReleaseMode(str(item.get("release_mode", "controlled")))
        except ValueError as exc:
            raise RuntimeError(f"{quote_id}: invalid release_mode") from exc
        quote = ApprovedQuote(
            id=quote_id,
            buyer_email=buyer_email,
            supplier_id=supplier_id,
            description=description,
            supplier_total_usd=supplier_total,
            list_price_usd=list_price,
            expires_at=_utc(expires_at),
            release_mode=release_mode,
        )
        if quote_id in quotes:
            raise RuntimeError(f"duplicate approved quote: {quote_id}")
        quotes[quote_id] = quote
    return quotes


def get_quote(quote_id: str, buyer_email: str) -> ApprovedQuote:
    quote = _load_quotes().get(quote_id.strip().upper())
    if not quote:
        raise ValueError("unknown or inactive quote code")
    if quote.expired:
        raise ValueError("this quote has expired")
    if quote.buyer_email != buyer_email.strip().lower():
        raise ValueError("buyer email does not match the approved quote")
    return quote


def quote_count() -> int:
    return len(_load_quotes())
