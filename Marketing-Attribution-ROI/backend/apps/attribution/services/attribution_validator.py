"""Validation, normalization, eligibility filtering, and reconciliation helpers for Attribution."""

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.web_sessions.models import WebSession

WEIGHT_QUANTUM = Decimal('0.000001')
WEIGHT_TOTAL = Decimal('1.000000')
ZERO_WEIGHT = Decimal('0.000000')
CURRENCY_QUANTUM = Decimal('0.01')
ZERO_MONEY = Decimal('0.00')


def ensure_utc_datetime(dt: datetime) -> datetime:
    """Normalize a datetime object to timezone-aware UTC."""
    if timezone.is_naive(dt):
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def order_conversion_cutoff(order: Order) -> datetime:
    """Convert an Order calendar date to end-of-day UTC cutoff (23:59:59Z)."""
    return datetime(
        order.order_date.year,
        order.order_date.month,
        order.order_date.day,
        23,
        59,
        59,
        tzinfo=dt_timezone.utc,
    )


def normalize_decimal_weights(
    raw_weights: list[Decimal],
    *,
    anchor_index: int | None = None,
) -> list[Decimal]:
    """
    Normalize non-negative weights into 6-decimal-place Credits summing strictly to 1.000000.
    Assigns any 10^-6 rounding remainder deterministically to `anchor_index` (or highest weight).
    """
    n = len(raw_weights)
    if n == 0:
        return []
    total_raw = sum(raw_weights, Decimal('0'))
    if total_raw <= 0:
        raw_weights = [Decimal('1')] * n
        total_raw = Decimal(n)

    scaled = [
        (w / total_raw).quantize(WEIGHT_QUANTUM, rounding=ROUND_HALF_UP)
        for w in raw_weights
    ]
    diff = WEIGHT_TOTAL - sum(scaled, ZERO_WEIGHT)
    if diff != ZERO_WEIGHT:
        if anchor_index is None:
            # Prefer last touchpoint among max raw weights for deterministic tie-breaking
            anchor_index = max(range(n), key=lambda idx: (raw_weights[idx], idx))
        scaled[anchor_index] += diff

    if any(w < ZERO_WEIGHT or w > WEIGHT_TOTAL for w in scaled):
        raise ValueError(f'Normalized weights out of [0, 1] bounds: {scaled}')
    if sum(scaled, ZERO_WEIGHT) != WEIGHT_TOTAL:
        raise ValueError(f'Normalized weights failed exact 1.000000 sum invariant: {scaled}')
    return scaled


def allocate_order_revenue(order_revenue: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """
    Split `order_revenue` proportionally by `weights` rounded to cents (`0.01`)
    so the exact sum matches `order_revenue` without rounding leakage.
    """
    if not weights:
        return []
    target = Decimal(order_revenue).quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
    splits = [
        (target * w).quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
        for w in weights
    ]
    remainder = target - sum(splits, ZERO_MONEY)
    if remainder != ZERO_MONEY:
        # Allocate cent adjustment onto highest-weight credited touchpoint
        positive_indices = [idx for idx, w in enumerate(weights) if w > ZERO_WEIGHT]
        anchor = (
            max(positive_indices, key=lambda idx: (weights[idx], idx))
            if positive_indices
            else len(weights) - 1
        )
        splits[anchor] += remainder
    return splits


def validate_order_eligibility(order: Order) -> tuple[bool, str]:
    """
    Verify an Order represents canonical non-duplicate paid revenue eligible for attribution.
    Returns `(is_eligible, exclusion_category)`.
    """
    if order.verification_status == Order.VerificationStatus.DUPLICATE:
        return False, 'duplicate'
    if order.verification_status != Order.VerificationStatus.VALID:
        return False, 'unverified'
    if order.payment_status != Order.PaymentStatus.PAID:
        return False, 'unpaid'
    return True, 'eligible'


def filter_eligible_touchpoints(
    touchpoints: list[Touchpoint],
    *,
    conversion_cutoff: datetime,
    conversion_window_days: int,
) -> tuple[list[Touchpoint], dict[str, int]]:
    """
    Filter a contact's touchpoints for attribution eligibility prior to `conversion_cutoff`:
      - Excludes post-conversion touches (`is_post_conversion=True` or timestamp > cutoff)
      - Excludes invalid touches (`is_valid=False`)
      - Excludes touches attached to unverified or cross-contact anonymous WebSessions
      - Excludes touches outside the `conversion_window_days` lookback window
      - Retains online AND offline touches and touches missing `campaign_id`
    """
    window_start = conversion_cutoff - timedelta(days=conversion_window_days)
    eligible: list[Touchpoint] = []
    stats = {
        'excluded_post_conversion': 0,
        'excluded_invalid': 0,
        'excluded_unverified_session': 0,
        'excluded_outside_window': 0,
    }

    for tp in touchpoints:
        tp_ts = ensure_utc_datetime(tp.timestamp)
        if tp.is_post_conversion or tp_ts > conversion_cutoff:
            stats['excluded_post_conversion'] += 1
            continue
        if not tp.is_valid:
            stats['excluded_invalid'] += 1
            continue
        if tp.session_id is not None:
            session = tp.session
            if (
                session is None
                or not session.has_evidence
                or session.identity_status != WebSession.IdentityStatus.IDENTIFIED
                or session.contact_id != tp.contact_id
            ):
                stats['excluded_unverified_session'] += 1
                continue
        if tp_ts < window_start:
            stats['excluded_outside_window'] += 1
            continue
        eligible.append(tp)

    eligible.sort(key=lambda item: (ensure_utc_datetime(item.timestamp), item.id))
    return eligible, stats


def verify_order_reconciliation(
    *,
    order_id: str,
    order_revenue: Decimal,
    weights: list[Decimal],
    revenues: list[Decimal],
) -> None:
    """Assert strict mathematical conservation of 100% credit and order revenue."""
    if not weights:
        return
    if len(weights) != len(revenues):
        raise ValueError(f'Order {order_id}: weight/revenue length mismatch.')
    weight_sum = sum(weights, ZERO_WEIGHT)
    if weight_sum != WEIGHT_TOTAL:
        raise ValueError(
            f'Order {order_id}: credit weights summed to {weight_sum}, expected {WEIGHT_TOTAL}.'
        )
    rev_sum = sum(revenues, ZERO_MONEY)
    expected_rev = Decimal(order_revenue).quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
    if rev_sum != expected_rev:
        raise ValueError(
            f'Order {order_id}: attributed revenue {rev_sum} != source order revenue {expected_rev}.'
        )

