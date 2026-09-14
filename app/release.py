"""Release-rule engine: decides when a supplier's held portion may be released.

Pure logic (no Stripe calls) so it is fully unit-testable. Thresholds come
from app.config; the bands below mirror the build plan:

- supplier_total < auto_release_max AND tracking present -> AUTO
- supplier_total >= manual_approval_min                    -> MANUAL
- anything in between needs delivery confirmation           -> ON_DELIVERY
- dispute/chargeback/refund requested at any time           -> FROZEN
"""
from dataclasses import dataclass
from enum import Enum

from .config import settings


class ReleaseDecision(str, Enum):
    AUTO = "auto"                # release now
    ON_DELIVERY = "on_delivery"  # hold until delivery confirmation
    MANUAL = "manual"            # Dominic approves, no exceptions
    FROZEN = "frozen"            # dispute/chargeback: never release while frozen


@dataclass
class ReleaseContext:
    supplier_total_usd: float
    tracking_number: str | None = None
    delivery_confirmed: bool = False
    dispute_open: bool = False
    manual_approved: bool = False


def decide(ctx: ReleaseContext) -> ReleaseDecision:
    if ctx.dispute_open:
        return ReleaseDecision.FROZEN
    if ctx.supplier_total_usd >= settings.manual_approval_min_usd:
        # Big tickets always need a human first; after approval, normal
        # delivery timing governs the release.
        if not ctx.manual_approved:
            return ReleaseDecision.MANUAL
        return ReleaseDecision.AUTO if ctx.delivery_confirmed else ReleaseDecision.ON_DELIVERY
    if ctx.delivery_confirmed:
        return ReleaseDecision.AUTO
    if ctx.supplier_total_usd < settings.auto_release_max_usd and ctx.tracking_number:
        return ReleaseDecision.AUTO
    return ReleaseDecision.ON_DELIVERY
