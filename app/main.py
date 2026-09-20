"""ORXYZ Marketplace API and Trade Desk.

Security model:
- buyer checkout accepts only quote_id + buyer_email;
- price, supplier cost, supplier account and release mode come from the
  server-side approved quote registry;
- live buyer charges, Connect supplier releases and instant splits are
  separately disabled by default;
- /ops endpoints require a long bearer token;
- Stripe webhooks reconcile Session, PaymentIntent and Charge IDs explicitly.
"""
from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

import stripe
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from .config import settings
from .po import (
    POState,
    append_note,
    create_po,
    get_po,
    get_po_by_charge,
    get_po_by_payment_intent,
    get_po_by_quote,
    get_po_by_session,
    list_pos,
    set_state,
    update_po,
)
from .quotes import ReleaseMode, get_quote, quote_count
from .release import ReleaseContext, ReleaseDecision, decide
from .stripe_client import create_checkout, payment_references, release_supplier_funds
from .suppliers import get_supplier
from .web import result_page, trade_desk_page
from .finance_web import wallet_page, control_page


app = FastAPI(title="ORXYZ Marketplace", docs_url=None, redoc_url=None)

_RATE_WINDOW = 60.0
_RATE_LIMIT = 12
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    value = forwarded.split(",", 1)[0].strip() or (request.client.host if request.client else "unknown")
    return value[:80]


def _rate_limit(request: Request) -> None:
    now = time.time()
    bucket = _rate_buckets[_client_ip(request)]
    while bucket and bucket[0] <= now - _RATE_WINDOW:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT:
        raise HTTPException(429, "too many checkout attempts; try again shortly")
    bucket.append(now)


def _require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    expected = urlparse(settings.base_url)
    supplied = urlparse(origin)
    if (expected.scheme, expected.netloc) != (supplied.scheme, supplied.netloc):
        raise HTTPException(403, "cross-site checkout requests are not allowed")


def _require_ops(authorization: str | None) -> None:
    if not settings.ops_configured:
        raise HTTPException(503, "operator controls are not configured")
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(401, "operator authorization required")
    token = authorization[len(prefix):].strip()
    if not hmac.compare_digest(token, settings.ops_token):
        raise HTTPException(403, "invalid operator authorization")


def _string_id(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return getattr(value, "id", None)


@app.get("/", include_in_schema=False)
def home():
    return trade_desk_page(checkout_enabled=settings.checkout_enabled)


@app.get("/wallet", include_in_schema=False)
def wallet():
    return wallet_page()


@app.get("/control", include_in_schema=False)
def control():
    return control_page()


@app.get("/success", include_in_schema=False)
def success():
    return result_page(success=True)


@app.get("/cancelled", include_in_schema=False)
def cancelled():
    return result_page(success=False)


@app.get("/health")
def health():
    return {
        "ok": True,
        "checkout_enabled": settings.checkout_enabled,
        "supplier_releases_enabled": settings.supplier_releases_enabled,
        "instant_splits_enabled": settings.instant_splits_enabled,
        "approved_quote_count": quote_count(),
        "ops_configured": settings.ops_configured,
    }


class CheckoutRequest(BaseModel):
    quote_id: str
    buyer_email: str


@app.post("/checkout")
def checkout(req: CheckoutRequest, request: Request):
    _rate_limit(request)
    _require_same_origin(request)
    if not settings.checkout_enabled:
        raise HTTPException(503, "ORXYZ checkout is staged but not enabled for live payments")

    try:
        quote = get_quote(req.quote_id, req.buyer_email)
        supplier = get_supplier(quote.supplier_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    existing = get_po_by_quote(quote.id)
    if existing:
        if existing["state"] == POState.PENDING.value and existing.get("stripe_session_id"):
            try:
                stripe.api_key = settings.stripe_secret_key
                session = stripe.checkout.Session.retrieve(existing["stripe_session_id"])
                if getattr(session, "status", None) == "open" and getattr(session, "url", None):
                    return {
                        "po_id": existing["id"],
                        "session_id": session.id,
                        "url": session.url,
                        "mode": quote.release_mode.value,
                        "rail": supplier.rail.value,
                    }
            except Exception:
                pass
        raise HTTPException(409, "this approved quote already has a checkout/order record; contact ORXYZ for a refreshed quote")

    po_id = create_po(
        quote_id=quote.id,
        buyer_email=quote.buyer_email,
        supplier_id=quote.supplier_id,
        supplier_total_usd=float(quote.supplier_total_usd),
        list_price_usd=float(quote.list_price_usd),
    )
    try:
        session = create_checkout(
            quote=quote,
            po_id=po_id,
            success_url=f"{settings.base_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.base_url}/cancelled",
        )
    except Exception as exc:
        append_note(po_id, f"checkout creation failed: {type(exc).__name__}")
        raise HTTPException(503, "secure checkout could not be created") from exc

    update_po(po_id, stripe_session_id=session["session_id"])
    return {"po_id": po_id, **session, "rail": supplier.rail.value}


def _mark_paid_session(obj) -> None:
    session_id = _string_id(obj.get("id"))
    if not session_id:
        return
    po = get_po_by_session(session_id)
    if not po:
        metadata = obj.get("metadata") or {}
        po_id = metadata.get("po_id") if hasattr(metadata, "get") else None
        po = get_po(str(po_id)) if po_id else None
    if not po:
        return
    if obj.get("payment_status") != "paid":
        return

    pi_id = _string_id(obj.get("payment_intent"))
    canonical_pi, charge_id = payment_references(pi_id)
    metadata = obj.get("metadata") or {}
    release_mode = metadata.get("release_mode") if hasattr(metadata, "get") else None

    fields = {
        "stripe_payment_intent_id": canonical_pi,
        "stripe_charge_id": charge_id,
    }
    if release_mode == ReleaseMode.INSTANT.value:
        set_state(po["id"], POState.RELEASED, **fields)
        append_note(po["id"], "instant destination split completed by Stripe")
    else:
        set_state(po["id"], POState.FUNDS_CLEARED, **fields)


def _freeze_for_charge(obj) -> None:
    charge_id = _string_id(obj.get("id"))
    pi_id = _string_id(obj.get("payment_intent"))
    po = get_po_by_charge(charge_id) if charge_id else None
    if not po and pi_id:
        po = get_po_by_payment_intent(pi_id)
    if po:
        set_state(po["id"], POState.FROZEN, dispute_open=1)
        append_note(po["id"], "Stripe dispute opened; supplier release frozen")


def _refund_for_charge(obj) -> None:
    charge_id = _string_id(obj.get("id"))
    pi_id = _string_id(obj.get("payment_intent"))
    po = get_po_by_charge(charge_id) if charge_id else None
    if not po and pi_id:
        po = get_po_by_payment_intent(pi_id)
    if po:
        set_state(po["id"], POState.REFUNDED)
        append_note(po["id"], "Stripe charge refunded")


@app.post("/webhook")
async def webhook(request: Request, stripe_signature: str | None = Header(None)):
    if not settings.stripe_configured:
        raise HTTPException(503, "Stripe webhooks are not configured")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            settings.stripe_webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(400, "invalid Stripe webhook signature") from exc

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        _mark_paid_session(obj)
    elif event_type == "charge.dispute.created":
        _freeze_for_charge(obj)
    elif event_type == "charge.refunded":
        _refund_for_charge(obj)
    return {"received": True}


def _maybe_release(po: dict) -> tuple[ReleaseDecision, str]:
    ctx = ReleaseContext(
        supplier_total_usd=po["supplier_total_usd"],
        tracking_number=po.get("tracking_number"),
        delivery_confirmed=po["state"] == POState.DELIVERED.value,
        dispute_open=bool(po.get("dispute_open")),
        manual_approved=bool(po.get("manual_approved")),
    )
    decision = decide(ctx)

    if decision is ReleaseDecision.FROZEN:
        set_state(po["id"], POState.FROZEN, dispute_open=1)
        return decision, "frozen"

    if decision is not ReleaseDecision.AUTO:
        return decision, "held"

    supplier = get_supplier(po["supplier_id"])
    if supplier.auto_split_possible:
        if not settings.supplier_releases_enabled:
            return decision, "approved_but_release_switch_off"
        charge_id = po.get("stripe_charge_id")
        if not charge_id:
            return decision, "approved_but_charge_id_missing"
        transfer_id = release_supplier_funds(
            charge_id=charge_id,
            supplier_id=po["supplier_id"],
            amount_usd=po["supplier_total_usd"],
            po_id=po["id"],
        )
        set_state(po["id"], POState.RELEASED, stripe_transfer_id=transfer_id)
        return decision, "stripe_transfer_released"

    # Manual-wire supplier: this app never originates the wire. The operator
    # must execute it through the bank/AP process, then explicitly mark wired.
    append_note(po["id"], "release rules satisfied; manual supplier payment still required")
    return decision, "manual_wire_required"


class OpsUpdate(BaseModel):
    tracking_number: str | None = None
    delivered: bool = False
    po_sent: bool = False
    manual_approved: bool = False
    wired: bool = False


@app.post("/ops/po/{po_id}")
def ops_update(po_id: str, upd: OpsUpdate, authorization: str | None = Header(None)):
    _require_ops(authorization)
    po = get_po(po_id)
    if not po:
        raise HTTPException(404, "unknown PO")
    if po["state"] in {POState.FROZEN.value, POState.REFUNDED.value, POState.RELEASED.value}:
        raise HTTPException(409, f"PO is already {po['state']}")

    fields: dict = {}
    if upd.tracking_number:
        tracking = upd.tracking_number.strip()
        if not tracking or len(tracking) > 160:
            raise HTTPException(400, "invalid tracking number")
        fields["tracking_number"] = tracking
    if upd.manual_approved:
        fields["manual_approved"] = 1

    state = POState(po["state"])
    if upd.po_sent:
        if state is not POState.FUNDS_CLEARED:
            raise HTTPException(409, "PO can be marked sent only after buyer funds are confirmed")
        state = POState.PO_SENT
    if upd.tracking_number:
        if state not in {POState.PO_SENT, POState.FUNDS_CLEARED, POState.SHIPPED}:
            raise HTTPException(409, "tracking can be added only after funds are confirmed")
        state = POState.SHIPPED
    if upd.delivered:
        if state not in {POState.SHIPPED, POState.PO_SENT}:
            raise HTTPException(409, "delivery can be confirmed only after PO/shipment")
        state = POState.DELIVERED

    set_state(po_id, state, **fields)
    po = get_po(po_id)

    if upd.wired:
        supplier = get_supplier(po["supplier_id"])
        if supplier.auto_split_possible:
            raise HTTPException(400, "Connect suppliers release through Stripe, not the manual-wire flag")
        if not settings.supplier_releases_enabled:
            raise HTTPException(503, "supplier release confirmation is disabled")
        if state not in {POState.SHIPPED, POState.DELIVERED, POState.PO_SENT}:
            raise HTTPException(409, "manual supplier payment cannot be marked before PO release stage")
        set_state(po_id, POState.RELEASED)
        append_note(po_id, "operator confirmed supplier payment was sent outside Stripe")
        return {"po_id": po_id, "state": POState.RELEASED.value, "release_decision": "manual_wire", "release_action": "operator_confirmed"}

    decision, action = _maybe_release(get_po(po_id))
    return {
        "po_id": po_id,
        "state": get_po(po_id)["state"],
        "release_decision": decision.value,
        "release_action": action,
    }


@app.get("/ops/pos")
def ops_list(state: str | None = None, authorization: str | None = Header(None)):
    _require_ops(authorization)
    try:
        parsed_state = POState(state) if state else None
    except ValueError as exc:
        raise HTTPException(400, "invalid PO state") from exc
    return list_pos(parsed_state)
