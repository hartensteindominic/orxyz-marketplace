"""Ledger behavior tests that do not require an external database."""
from app.config import settings
from app.po import POState, create_po, get_po, list_pos, set_state, update_po


def test_sqlite_staging_ledger_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", "")
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "orxyz-test.db"))

    po_id = create_po(
        quote_id="Q-TEST-1",
        buyer_email="buyer@example.com",
        supplier_id="supplier-test",
        supplier_total_usd=800.0,
        list_price_usd=1000.0,
    )

    po = get_po(po_id)
    assert po is not None
    assert po["quote_id"] == "Q-TEST-1"
    assert po["state"] == POState.PENDING.value
    assert po["spread_usd"] == 200.0

    update_po(po_id, stripe_session_id="cs_test_example")
    set_state(po_id, POState.FUNDS_CLEARED, stripe_charge_id="ch_test_example")

    updated = get_po(po_id)
    assert updated is not None
    assert updated["state"] == POState.FUNDS_CLEARED.value
    assert updated["stripe_session_id"] == "cs_test_example"
    assert updated["stripe_charge_id"] == "ch_test_example"

    funded = list_pos(POState.FUNDS_CLEARED)
    assert [item["id"] for item in funded] == [po_id]
