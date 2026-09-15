"""Tests for server-side approved quote binding."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.config import settings
from app.quotes import ReleaseMode, get_quote


def _quote(*, expires_at: datetime | None = None, list_price: str = "1000.00") -> str:
    expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(days=7))
    return json.dumps([
        {
            "id": "ORXYZ-Q-TEST-001",
            "buyer_email": "buyer@example.com",
            "supplier_id": "conexdepot",
            "description": "Approved industrial supply test quote",
            "supplier_total_usd": "800.00",
            "list_price_usd": list_price,
            "expires_at": expires_at.isoformat(),
            "release_mode": "controlled",
        }
    ])


def test_quote_locks_server_side_economics(monkeypatch):
    monkeypatch.setattr(settings, "approved_quotes_json", _quote())
    quote = get_quote("orxyz-q-test-001", "BUYER@example.com")

    assert quote.supplier_total_usd == Decimal("800.00")
    assert quote.list_price_usd == Decimal("1000.00")
    assert quote.spread_usd == Decimal("200.00")
    assert quote.release_mode is ReleaseMode.CONTROLLED


def test_quote_rejects_wrong_buyer(monkeypatch):
    monkeypatch.setattr(settings, "approved_quotes_json", _quote())
    with pytest.raises(ValueError, match="buyer email"):
        get_quote("ORXYZ-Q-TEST-001", "other@example.com")


def test_quote_rejects_expired_quote(monkeypatch):
    monkeypatch.setattr(
        settings,
        "approved_quotes_json",
        _quote(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)),
    )
    with pytest.raises(ValueError, match="expired"):
        get_quote("ORXYZ-Q-TEST-001", "buyer@example.com")


def test_registry_rejects_quote_without_positive_spread(monkeypatch):
    monkeypatch.setattr(settings, "approved_quotes_json", _quote(list_price="800.00"))
    with pytest.raises(RuntimeError, match="list price must exceed supplier cost"):
        get_quote("ORXYZ-Q-TEST-001", "buyer@example.com")
