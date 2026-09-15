# ORXYZ Marketplace — controlled industrial checkout

ORXYZ Marketplace is the secure payment/settlement layer for ORXYZ principal-resale transactions:

**buyer accepts an ORXYZ quote → buyer pays ORXYZ → payment is verified → ORXYZ confirms the supplier PO → supplier direct-ships → supplier cost is released under the approved rail → ORXYZ retains the trading spread subject to fees, taxes, refunds, claims and reserves.**

## Buyer-facing Trade Desk

The FastAPI root page is a branded ORXYZ Trade Desk. Buyers enter only:

- their approved ORXYZ quote code; and
- the buyer email bound to that quote.

The browser **cannot supply or change** supplier cost, ORXYZ selling price, connected-account ID, supplier rail or payout timing. Those values come from the server-side approved quote registry.

## Two settlement rails

### ORXYZ Trade — default

Controlled settlement for custom, new-supplier and higher-value industrial transactions.

1. Stripe charges the buyer on the ORXYZ platform account.
2. Webhooks reconcile the Checkout Session, PaymentIntent and Charge IDs.
3. ORXYZ confirms buyer funds / PO stage.
4. The release engine applies shipment, delivery, dispute and manual-approval rules.
5. Eligible Connect suppliers receive a later Stripe transfer; manual-wire suppliers remain a human bank/AP action.

### ORXYZ Instant — exception

An approved quote may use an immediate destination-charge split only when:

- the supplier is eligible and onboarded to Stripe Connect;
- the approved quote explicitly uses `release_mode=instant`; and
- `INSTANT_SPLITS_ENABLED=true` is deliberately enabled server-side.

## Fail-closed live controls

Live checkout is **off by default**. `checkout_enabled` becomes true only when all of these are present:

- `LIVE_PAYMENTS_ENABLED=true`
- `DURABLE_LEDGER_ENABLED=true`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- a non-empty `ORXYZ_APPROVED_QUOTES_JSON`

Supplier payout is independently gated by `SUPPLIER_RELEASES_ENABLED=true`.

The included SQLite PO ledger is useful for local/manual staging, but it is **not treated as a durable serverless production ledger**. Do not turn on `DURABLE_LEDGER_ENABLED` on a serverless deployment until a persistent transaction store is actually attached and the ledger adapter has been updated accordingly.

## Operator controls

`/ops/*` endpoints require `Authorization: Bearer <ORXYZ_OPS_TOKEN>` and remain unavailable unless the server-side token is at least 24 characters.

The operator lifecycle is:

`PENDING → FUNDS_CLEARED → PO_SENT → SHIPPED → DELIVERED → RELEASED`

A Stripe dispute freezes the PO. A refund marks it refunded. Large orders still require the manual-approval rule before release.

## Project layout

- `app/main.py` — FastAPI Trade Desk, checkout, Stripe webhooks and protected operator routes
- `app/web.py` — branded buyer-facing Trade Desk pages
- `app/quotes.py` — server-side approved quote registry and pricing/buyer binding
- `app/stripe_client.py` — Checkout, destination-split and controlled-transfer helpers
- `app/po.py` — PO/order ledger
- `app/release.py` — pure release-rule engine
- `app/suppliers.py` — supplier registry and rail classification
- `app/config.py` — fail-closed environment controls
- `tests/` — quote, configuration and release-rule tests

## Local validation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m compileall -q app
pytest -q
uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` for local configuration. Never commit real Stripe keys, operator tokens or buyer quote data.

## Vercel

`pyproject.toml` declares `app.main:app` as the FastAPI entrypoint and `vercel.json` configures the Python function. A staged deployment is safe with the live switches left at their default `false` values.
