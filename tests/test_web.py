"""Smoke tests for the ORXYZ Trade Desk HTML."""
from app.web import result_page, trade_desk_page


def _html(response) -> str:
    return response.body.decode("utf-8")


def test_staged_trade_desk_disables_checkout():
    html = _html(trade_desk_page(checkout_enabled=False))
    assert "Checkout staged" in html
    assert "Checkout not enabled yet" in html
    assert "button type=\"submit\" disabled" in html


def test_live_trade_desk_renders_checkout_action():
    html = _html(trade_desk_page(checkout_enabled=True))
    assert "Checkout live" in html
    assert "Open secure checkout" in html
    assert "fetch('/checkout'" in html


def test_result_pages_render():
    assert "Payment received" in _html(result_page(success=True))
    assert "Checkout cancelled" in _html(result_page(success=False))
