"""Stripe money movement: checkout, splits, holds, releases.

Two patterns (see build plan):
- Destination charge + application_fee: immediate auto-split to a connected
  supplier account. Small tickets, trusted suppliers.
- Separate charge + transfer: charge the buyer now, transfer the supplier
  portion later when release rules allow. Big tickets, new suppliers.

Manual-wire rail suppliers never touch this module: buyer pays ORXYZ via a
plain PaymentIntent/Checkout, and the supplier is paid by wire after funds
clear (existing doctrine, human-executed until Stage 3+).
"""
import stripe

from .config import settings
from .suppliers import Rail, get_supplier

stripe.api_key = settings.stripe_secret_key


def cents(usd: float) -> int:
    return int(round(usd * 100))


def create_checkout(*, buyer_email: str, supplier_id: str,
                    supplier_total_usd: float, list_price_usd: float,
                    success_url: str, cancel_url: str,
                    immediate_split: bool = False) -> dict:
    """Create a Checkout Session. Returns {session_id, url, mode}.

    immediate_split=True uses a destination charge with application_fee
    (auto-split at payment). False (default) keeps the full charge on the
    platform so the supplier portion can be released later.
    """
    supplier = get_supplier(supplier_id)
    params: dict = {
        "mode": "payment",
        "customer_email": buyer_email,
        "line_items": [{
            "price_data": {
                "currency": "usd",
                "unit_amount": cents(list_price_usd),
                "product_data": {
                    "name": f"ORXYZ industrial supply via {supplier.name}",
                    "description": "Factory-direct industrial supply. Supplier ships directly to buyer.",
                },
            },
            "quantity": 1,
        }],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {
            "supplier_id": supplier_id,
            "supplier_total_usd": str(supplier_total_usd),
            "list_price_usd": str(list_price_usd),
            "rail": supplier.rail.value,
        },
    }
    if immediate_split:
        if supplier.rail is not Rail.CONNECT or not supplier.connect_account_id:
            raise ValueError(f"immediate split requires an onboarded Connect supplier: {supplier_id}")
        spread = list_price_usd - supplier_total_usd
        params["payment_intent_data"] = {
            "application_fee_amount": cents(spread),
            "transfer_data": {"destination": supplier.connect_account_id},
        }
    session = stripe.checkout.Session.create(**params)
    return {"session_id": session.id, "url": session.url,
            "mode": "immediate_split" if immediate_split else "held"}


def release_supplier_funds(*, payment_intent_id: str, supplier_id: str,
                           amount_usd: float) -> str:
    """Transfer the held supplier portion (separate charges & transfers)."""
    supplier = get_supplier(supplier_id)
    if supplier.rail is not Rail.CONNECT or not supplier.connect_account_id:
        raise ValueError(f"API release requires an onboarded Connect supplier: {supplier_id}")
    transfer = stripe.Transfer.create(
        amount=cents(amount_usd),
        currency="usd",
        destination=supplier.connect_account_id,
        source_transaction=payment_intent_id,
        metadata={"purpose": "orxyz supplier cost release"},
    )
    return transfer.id


def create_express_account_link(*, supplier_id: str, refresh_url: str,
                                return_url: str) -> dict:
    """Start Connect Express onboarding for an eligible supplier."""
    supplier = get_supplier(supplier_id)
    if supplier.rail is not Rail.CONNECT and supplier.country in {"CN", "TR"}:
        raise ValueError(f"{supplier.name} ({supplier.country}) cannot onboard to Stripe Connect")
    account = stripe.Account.create(type="express", country=supplier.country,
                                    email=None, capabilities={
                                        "transfers": {"requested": True},
                                    })
    link = stripe.AccountLink.create(
        account=account.id, refresh_url=refresh_url, return_url=return_url,
        type="account_onboarding")
    return {"account_id": account.id, "onboarding_url": link.url}
