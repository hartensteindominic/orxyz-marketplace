"""FastAPI app: checkout creation + Stripe webhook -> PO lifecycle.

Webhook flow:
  checkout.session.completed -> PO FUNDS_CLEARED (funds verified settled,
      not just authorized) -> human/system sends PO -> PO_SENT
  operator marks tracking        -> SHIPPED (auto-release evaluated)
  operator marks delivery        -> DELIVERED (auto-release evaluated)
  charge.dispute.created         -> FROZEN (never auto-release while frozen)
  release approved by rules      -> RELEASED (Connect rail: API transfer;
                                   manual-wire rail: operator wires + marks)
"""
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

import stripe

from .config import settings
from .po import POState, create_po, get_po, list_pos, set_state
from .release import ReleaseContext, ReleaseDecision, decide
from .stripe_client import create_checkout, release_supplier_funds
from .suppliers import get_supplier

stripe.api_key = settings.stripe_secret_key

app = FastAPI(title="ORXYZ Marketplace")


class CheckoutRequest(BaseModel):
    buyer_email: str
    supplier_id: str
    supplier_total_usd: float
    list_price_usd: float
    immediate_split: bool = False  # default: hold, release per rules


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/checkout")
def checkout(req: CheckoutRequest):
    if req.list_price_usd <= req.supplier_total_usd:
        raise HTTPException(400, "list price must exceed supplier cost (the spread is the business)")
    supplier = get_supplier(req.supplier_id)
    sess = create_checkout(
        buyer_email=req.buyer_email, supplier_id=req.supplier_id,
        supplier_total_usd=req.supplier_total_usd, list_price_usd=req.list_price_usd,
        success_url=f"{settings.base_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.base_url}/cancelled",
        immediate_split=req.immediate_split,
    )
    po_id = create_po(buyer_email=req.buyer_email, supplier_id=req.supplier_id,
                      supplier_total_usd=req.supplier_total_usd,
                      list_price_usd=req.list_price_usd)
    set_state(po_id, POState.PENDING, stripe_payment_intent=sess["session_id"])
    return {"po_id": po_id, **sess, "rail": supplier.rail.value}


def _maybe_release(po: dict) -> ReleaseDecision:
    ctx = ReleaseContext(
        supplier_total_usd=po["supplier_total_usd"],
        tracking_number=po["tracking_number"],
        delivery_confirmed=po["state"] == POState.DELIVERED.value,
        dispute_open=bool(po["dispute_open"]),
        manual_approved=bool(po["manual_approved"]),
    )
    decision = decide(ctx)
    if decision is ReleaseDecision.AUTO:
        supplier = get_supplier(po["supplier_id"])
        if supplier.auto_split_possible and po["stripe_payment_intent"]:
            transfer_id = release_supplier_funds(
                payment_intent_id=po["stripe_payment_intent"],
                supplier_id=po["supplier_id"],
                amount_usd=po["supplier_total_usd"])
            set_state(po["id"], POState.RELEASED, stripe_transfer_id=transfer_id)
        else:
            # Manual-wire rail: operator wires the supplier, then marks released
            # via /ops/release. We only record that rules approved the release.
            set_state(po["id"], POState.PO_SENT,
                      notes=(po["notes"] + " | release approved by rules; awaiting wire").strip(" |"))
    elif decision is ReleaseDecision.FROZEN:
        set_state(po["id"], POState.FROZEN)
    return decision


@app.post("/webhook")
async def webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature,
                                               settings.stripe_webhook_secret)
    except Exception as e:
        raise HTTPException(400, f"bad signature: {e}")
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        session_id = obj["id"]
        po = next((p for p in list_pos(POState.PENDING)
                   if p["stripe_payment_intent"] == session_id), None)
        # Only mark cleared when Stripe reports the payment as paid/settled.
        if po and obj.get("payment_status") == "paid":
            set_state(po["id"], POState.FUNDS_CLEARED)
    elif etype == "charge.dispute.created":
        pi = obj.get("payment_intent")
        for po in list_pos():
            if po["stripe_payment_intent"] == pi or po["stripe_payment_intent"] == obj.get("id"):
                set_state(po["id"], POState.FROZEN, dispute_open=1)
    return {"received": True}


class OpsUpdate(BaseModel):
    tracking_number: str | None = None
    delivered: bool = False
    po_sent: bool = False
    manual_approved: bool = False
    wired: bool = False  # manual-wire rail: operator confirms the wire went out


@app.post("/ops/po/{po_id}")
def ops_update(po_id: str, upd: OpsUpdate):
    po = get_po(po_id)
    if not po:
        raise HTTPException(404, "unknown PO")
    fields: dict = {}
    if upd.tracking_number:
        fields["tracking_number"] = upd.tracking_number
    if upd.manual_approved:
        fields["manual_approved"] = 1
    state = POState[po["state"].upper()]
    if upd.po_sent and state == POState.FUNDS_CLEARED:
        state = POState.PO_SENT
    if upd.tracking_number and state in (POState.PO_SENT, POState.FUNDS_CLEARED):
        state = POState.SHIPPED
    if upd.delivered:
        state = POState.DELIVERED
    if upd.wired and state in (POState.SHIPPED, POState.DELIVERED, POState.PO_SENT):
        # Manual-wire rail only: the wire is the release.
        supplier = get_supplier(po["supplier_id"])
        if supplier.auto_split_possible:
            raise HTTPException(400, "Connect-rail suppliers release via API transfer, not manual wire flag")
        state = POState.RELEASED
    set_state(po_id, state, **fields)
    po = get_po(po_id)
    decision = _maybe_release(po)
    return {"po_id": po_id, "state": get_po(po_id)["state"], "release_decision": decision.value}


@app.get("/ops/pos")
def ops_list(state: str | None = None):
    return list_pos(POState(state) if state else None)
