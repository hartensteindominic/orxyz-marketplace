"""Unit tests for the release-rule engine (pure logic, no Stripe calls)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.release import ReleaseContext, ReleaseDecision, decide


def test_small_ticket_with_tracking_auto_releases():
    ctx = ReleaseContext(supplier_total_usd=800, tracking_number="1Z999")
    assert decide(ctx) is ReleaseDecision.AUTO


def test_small_ticket_without_tracking_waits_for_delivery():
    ctx = ReleaseContext(supplier_total_usd=800)
    assert decide(ctx) is ReleaseDecision.ON_DELIVERY


def test_mid_ticket_needs_delivery_confirmation():
    ctx = ReleaseContext(supplier_total_usd=12000, tracking_number="1Z999")
    assert decide(ctx) is ReleaseDecision.ON_DELIVERY
    ctx2 = ReleaseContext(supplier_total_usd=12000, tracking_number="1Z999",
                          delivery_confirmed=True)
    assert decide(ctx2) is ReleaseDecision.AUTO


def test_big_ticket_needs_manual_approval_even_when_delivered():
    ctx = ReleaseContext(supplier_total_usd=60000, delivery_confirmed=True)
    assert decide(ctx) is ReleaseDecision.MANUAL
    ctx2 = ReleaseContext(supplier_total_usd=60000, delivery_confirmed=True,
                         manual_approved=True)
    # manual approval unlocks; delivery confirmation then governs timing
    assert decide(ctx2) is ReleaseDecision.AUTO


def test_dispute_freezes_everything():
    ctx = ReleaseContext(supplier_total_usd=800, tracking_number="1Z999",
                         delivery_confirmed=True, manual_approved=True,
                         dispute_open=True)
    assert decide(ctx) is ReleaseDecision.FROZEN
