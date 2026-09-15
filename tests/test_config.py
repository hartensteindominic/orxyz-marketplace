"""Tests for fail-closed live payment configuration."""
from app.config import settings


def test_checkout_stays_off_without_durable_ledger(monkeypatch):
    monkeypatch.setattr(settings, "live_payments_enabled", True)
    monkeypatch.setattr(settings, "durable_ledger_enabled", False)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_example")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_example")
    monkeypatch.setattr(settings, "approved_quotes_json", "[{}]")
    assert settings.checkout_enabled is False


def test_checkout_requires_every_live_gate(monkeypatch):
    monkeypatch.setattr(settings, "live_payments_enabled", True)
    monkeypatch.setattr(settings, "durable_ledger_enabled", True)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_example")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_example")
    monkeypatch.setattr(settings, "approved_quotes_json", "[{}]")
    assert settings.checkout_enabled is True


def test_ops_requires_long_server_token(monkeypatch):
    monkeypatch.setattr(settings, "ops_token", "short")
    assert settings.ops_configured is False
    monkeypatch.setattr(settings, "ops_token", "x" * 32)
    assert settings.ops_configured is True
