# ORXYZ Marketplace — Stripe Connect money rails

Principal-spread automation for ORXYZ's industrial sourcing business:
buyer pays ORXYZ → supplier is paid their cost → ORXYZ keeps the spread →
supplier direct-ships to the buyer.

## Two money rails (see `app/suppliers.py`)

- **Connect rail** — suppliers in Stripe-supported countries (US, EU/UK,
  Switzerland, Japan, Singapore, Hong Kong, UAE…). Automatic split via
  destination charges, or timed transfers via separate charges & transfers.
- **Manual-wire rail** — mainland-China and Turkey suppliers (not
  Stripe-supported). Buyer pays ORXYZ; ORXYZ wires the supplier after funds
  clear, per the standing principal-spread doctrine.

## Release rules (see `app/release.py`)

- <$5,000 + tracking number → auto-release
- $5,000–$25,000 → release on delivery confirmation
- >$25,000 → manual approval only
- Any dispute/chargeback → freeze immediately

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
uvicorn app.main:app --reload
```

## Layout

- `app/main.py` — FastAPI: checkout session creation + Stripe webhook
- `app/stripe_client.py` — charge / split / hold / release helpers
- `app/release.py` — the release-rule engine (pure logic, fully tested)
- `app/po.py` — PO ledger (sqlite): PENDING → FUNDS_CLEARED → PO_SENT →
  SHIPPED → DELIVERED → RELEASED / FROZEN
- `app/suppliers.py` — supplier registry with rail classification
- `app/config.py` — env + thresholds

## Status

Staged build. Stage 1 (single Payment Link lane) goes live only after the
first manual principal-spread dollar lands; see
`../orxyz/stripe-connect-marketplace-build-plan-2026-09-14.md`.
