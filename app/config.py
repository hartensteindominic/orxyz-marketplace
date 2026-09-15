"""ORXYZ Marketplace configuration.

Real buyer charges and supplier releases are independently fail-closed. A
production deploy can safely render the Trade Desk before Stripe secrets,
approved quotes, operator auth, and a durable order ledger are configured.
"""
import os


def _f(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _b(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self):
        self.stripe_secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
        self.stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
        self.stripe_publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "").strip()
        self.database_path = os.environ.get("DATABASE_PATH", "./orxyz_marketplace.db")
        self.base_url = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

        # Both switches must be explicitly enabled for live money movement.
        self.live_payments_enabled = _b("LIVE_PAYMENTS_ENABLED", False)
        self.supplier_releases_enabled = _b("SUPPLIER_RELEASES_ENABLED", False)
        self.instant_splits_enabled = _b("INSTANT_SPLITS_ENABLED", False)

        # SQLite is fine for local/manual staging, but serverless filesystems are
        # not a durable transaction ledger. Keep live checkout off until ORXYZ
        # has attached a persistent ledger and explicitly acknowledges it here.
        self.durable_ledger_enabled = _b("DURABLE_LEDGER_ENABLED", False)

        # Keep quote economics and buyer assignment server-side.
        self.approved_quotes_json = os.environ.get("ORXYZ_APPROVED_QUOTES_JSON", "")

        # Required for /ops/* mutations and order visibility.
        self.ops_token = os.environ.get("ORXYZ_OPS_TOKEN", "").strip()

        self.auto_release_max_usd = _f("AUTO_RELEASE_MAX_USD", 5000.0)
        self.manual_approval_min_usd = _f("MANUAL_APPROVAL_MIN_USD", 25000.0)
        self.rolling_reserve_pct = _f("ROLLING_RESERVE_PCT", 0.10)
        self.rolling_reserve_floor_usd = _f("ROLLING_RESERVE_FLOOR_USD", 500.0)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_webhook_secret)

    @property
    def checkout_enabled(self) -> bool:
        return (
            self.live_payments_enabled
            and self.durable_ledger_enabled
            and self.stripe_configured
            and bool(self.approved_quotes_json.strip())
        )

    @property
    def ops_configured(self) -> bool:
        return len(self.ops_token) >= 24


settings = Settings()
