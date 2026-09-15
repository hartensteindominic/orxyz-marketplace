"""Stripe money movement helpers for ORXYZ Marketplace.

Controlled settlement is the default:
- buyer pays ORXYZ;
- the charge remains on the ORXYZ platform account;
- ORXYZ verifies the order / PO lifecycle;
- the supplier portion is transferred only after release controls allow it.

Instant destination-charge splitting exists only for an explicitly approved
quote and is separately disabled by default.
"""
from decimal import Decimal, ROUND_HALF_UP

import stripe

from .config import settings
from .quotes import ApprovedQuote, ReleaseMode
from .suppliers import Rail, get_supplier


MONEY = Decimal("0.01")


def _client_ready() -> None:
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.stripe_secret_key


def cents(usd: Decimal | float | str) -> int:
    amount = Decimal(str(usd)).quantize(MONEY, rounding=ROUND_HALF_UP)
    return int(amount * 100)


def create_checkout(*, quote: ApprovedQuote, po_id: str,
                    success_url: str, cancel_url: str) -> dict:
    """Create a Checkout Session from a server-side approved quote."""
    if not settings.checkout_enabled:
        raise RuntimeError("live checkout is disabled")
    _client_ready()

    supplier = get_supplier(quote.supplier_id)
    immediate_split = quote.release_mode is ReleaseMode.INSTANT
    if immediate_split and not settings.instant_splits_enabled:
        raise RuntimeError("instant split is disabled")
    if immediate_split and (supplier.rail is not Rail.CONNECT or not supplier.connect_account_id):
        raise RuntimeError("instant split requires an onboarded Connect supplier")

    payment_intent_data: dict = {
        "metadata": {
            "po_id": po_id,
            "quote_id": quote.id,
            "supplier_id": quote.supplier_id,
        }
    }

    if immediate_split:
        payment_intent_data.update({
            "application_fee_amount": cents(quote.spread_usd),
            "transfer_data": {"destination": supplier.connect_account_id},
        })
    else:
        # transfer_group links the later supplier transfer to this order.
        payment_intent_data["transfer_group"] = po_id

    params = {
        "mode": "payment",
        "customer_email": quote.buyer_email,
        "billing_address_collection": "required",
        "line_items": [{
            "price_data": {
                "currency": "usd",
                "unit_amount": cents(quote.list_price_usd),
                "product_data": {
                    "name": "ORXYZ approved industrial supply quote",
                    "description": quote.description[:500],
                },
            },
            "quantity": 1,
        }],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": po_id,
        "metadata": {
            "po_id": po_id,
            "quote_id": quote.id,
            "supplier_id": quote.supplier_id,
            "release_mode": quote.release_mode.value,
        },
        "payment_intent_data": payment_intent_data,
    }

    session = stripe.checkout.Session.create(
        **params,
        idempotency_key=f"orxyz:{quote.id}:checkout",
    )
    return {
        "session_id": session.id,
        "url": session.url,
        "mode": "instant_split" if immediate_split else "controlled",
    }


def payment_references(payment_intent_id: str | None) -> tuple[str | None, str | None]:
    """Return canonical PaymentIntent and latest Charge IDs."""
    if not payment_intent_id:
        return None, None
    _client_ready()
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    latest_charge = getattr(payment_intent, "latest_charge", None)
    if isinstance(latest_charge, str):
        charge_id = latest_charge
    elif latest_charge is not None:
        charge_id = getattr(latest_charge, "id", None)
    else:
        charge_id = None
    return payment_intent.id, charge_id


def release_supplier_funds(*, charge_id: str, supplier_id: str,
                           amount_usd: float, po_id: str) -> str:
    """Release the supplier portion for a controlled Connect order.

    Stripe separate charges and transfers links the transfer to the platform
    charge via source_transaction, which must be a Charge ID (ch_...), not a
    Checkout Session or PaymentIntent ID.
    """
    if not settings.supplier_releases_enabled:
        raise RuntimeError("supplier releases are disabled")
    _client_ready()

    supplier = get_supplier(supplier_id)
    if supplier.rail is not Rail.CONNECT or not supplier.connect_account_id:
        raise ValueError(f"API release requires an onboarded Connect supplier: {supplier_id}")
    if not charge_id.startswith("ch_"):
        raise ValueError("supplier release requires a Stripe Charge ID")

    transfer = stripe.Transfer.create(
        amount=cents(amount_usd),
        currency="usd",
        destination=supplier.connect_account_id,
        source_transaction=charge_id,
        transfer_group=po_id,
        metadata={"purpose": "orxyz supplier cost release", "po_id": po_id},
        idempotency_key=f"orxyz:{po_id}:supplier-release",
    )
    return transfer.id


def create_express_account_link(*, supplier_id: str, refresh_url: str,
                                return_url: str) -> dict:
    """Start Connect Express onboarding for an eligible supplier."""
    _client_ready()
    supplier = get_supplier(supplier_id)
    if supplier.country in {"CN", "TR"}:
        raise ValueError(f"{supplier.name} ({supplier.country}) is not configured for Connect onboarding")
    account = stripe.Account.create(
        type="express",
        country=supplier.country,
        capabilities={"transfers": {"requested": True}},
    )
    link = stripe.AccountLink.create(
        account=account.id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return {"account_id": account.id, "onboarding_url": link.url}
