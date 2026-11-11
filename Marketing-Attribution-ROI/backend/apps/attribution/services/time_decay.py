"""
Time-Decay attribution model calculator using explicit exponential half-life decay.

Formula:
    raw_weight_i = 2 ^ (-age_days_i / half_life_days)
    age_days_i   = max(0, (conversion_cutoff - touchpoint_timestamp_i) / 86400s)
    weight_i     = raw_weight_i / sum_j(raw_weight_j)

With default `half_life_days = 7`, a touchpoint occurring 7 days before conversion
receives half the raw weight of a touchpoint occurring on the conversion date.
"""

from datetime import datetime
from decimal import Decimal

from apps.attribution.services.attribution_validator import (
    ensure_utc_datetime,
    normalize_decimal_weights,
)
from apps.touchpoints.models import Touchpoint


def calculate_weights(
    touchpoints: list[Touchpoint],
    *,
    conversion_cutoff: datetime,
    half_life_days: int = 7,
) -> list[Decimal]:
    """Compute normalized exponential decay credits rewarding proximity to conversion."""
    n = len(touchpoints)
    if n == 0:
        return []
    if half_life_days <= 0:
        raise ValueError('half_life_days must be a positive integer.')
    if n == 1:
        return normalize_decimal_weights([Decimal('1')], anchor_index=0)

    cutoff_utc = ensure_utc_datetime(conversion_cutoff)
    raw_weights: list[Decimal] = []
    for tp in touchpoints:
        tp_utc = ensure_utc_datetime(tp.timestamp)
        age_seconds = max(0.0, (cutoff_utc - tp_utc).total_seconds())
        age_days = age_seconds / 86400.0
        raw_val = 2.0 ** (-age_days / float(half_life_days))
        raw_weights.append(Decimal(f'{raw_val:.12f}'))

    return normalize_decimal_weights(raw_weights, anchor_index=n - 1)

