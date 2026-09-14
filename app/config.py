"""App configuration: env vars + tunable release thresholds (stdlib only)."""
import os


def _f(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


class Settings:
    def __init__(self):
        self.stripe_secret_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_placeholder")
        self.stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
        self.stripe_publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_placeholder")
        self.database_path = os.environ.get("DATABASE_PATH", "./orxyz_marketplace.db")
        self.base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        self.auto_release_max_usd = _f("AUTO_RELEASE_MAX_USD", 5000.0)
        self.manual_approval_min_usd = _f("MANUAL_APPROVAL_MIN_USD", 25000.0)
        self.rolling_reserve_pct = _f("ROLLING_RESERVE_PCT", 0.10)
        self.rolling_reserve_floor_usd = _f("ROLLING_RESERVE_FLOOR_USD", 500.0)


settings = Settings()
