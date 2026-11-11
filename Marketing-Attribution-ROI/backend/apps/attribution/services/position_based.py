"""
Position-Based (U-Shaped) attribution model calculator:
  - N == 1: 100% credit to the single eligible touchpoint
  - N == 2: 50% / 50% credit split cleanly without distortion
  - N >= 3: 40% First Touch, 40% Last Touch, 20% shared equally across middle touches
"""

from datetime import datetime
from decimal import Decimal

from apps.attribution.services.attribution_validator import (
    WEIGHT_TOTAL,
    normalize_decimal_weights,
)
from apps.touchpoints.models import Touchpoint


def calculate_weights(
    touchpoints: list[Touchpoint],
    *,
    conversion_cutoff: datetime | None = None,
    half_life_days: int = 7,
) -> list[Decimal]:
    """Distribute credits using 40/20/40 U-shaped rules with exact 1.000000 sum."""
    n = len(touchpoints)
    if n == 0:
        return []
    if n == 1:
        return [WEIGHT_TOTAL]
    if n == 2:
        half = Decimal('0.500000')
        return [half, half]

    middle_count = n - 2
    middle_weights = normalize_decimal_weights(
        [Decimal('1')] * middle_count,
        anchor_index=middle_count - 1,
    )
    first_last = Decimal('0.400000')
    middle_pool = Decimal('0.200000')

    weights = [first_last]
    scaled_middles = [
        (w * middle_pool).quantize(Decimal('0.000001'))
        for w in middle_weights
    ]
    mid_diff = middle_pool - sum(scaled_middles, Decimal('0.000000'))
    if mid_diff != Decimal('0.000000'):
        scaled_middles[-1] += mid_diff

    weights.extend(scaled_middles)
    weights.append(first_last)
    return weights

