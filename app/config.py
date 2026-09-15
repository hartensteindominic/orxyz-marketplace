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

        # SQLite remains the local/manual staging default. DATABASE_URL is the
        # production ledger and must point to PostgreSQL before live checkout
        # can be enabled.
        self.database_path = os.environ.get("DATABASE_PATH", "./orxyz_marketplace.db")
        self.database_url = os.environ.get("DATABASE_URL", "").strip()
        self.base_url = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

        # Buyer charging and supplier release are intentionally independent.
        self.live_payments_enabled = _b("LIVE_PAYMENTS_ENABLED", False)
        self.supplier_releases_enabled = _b("SUPPLIER_RELEASES_ENABLED", False)
        self.instant_splits_enabled = _b("INSTANT_SPLITS_ENABLED", False)

        # This is an operator acknowledgement, not proof by itself. The
        # checkout_enabled property also verifies a supported durable backend.
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
    def durable_database_configured(self) -> bool:
        """Return true only for the durable backend supported by app.po."""
        url = self.database_url.lower()
        return url.startswith("postgresql://") or url.startswith("postgres://")

    @property
    def checkout_enabled(self) -> bool:
        return (
            self.live_payments_enabled
            and self.durable_ledger_enabled
            and self.durable_database_configured
            and self.stripe_configured
            and bool(self.approved_quotes_json.strip())
        )

    @property
    def ops_configured(self) -> bool:
        return len(self.ops_token) >= 24


settings = Settings()
