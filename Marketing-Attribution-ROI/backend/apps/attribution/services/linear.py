"""Linear attribution model calculator (equal distribution across all eligible touches)."""

from datetime import datetime
from decimal import Decimal

from apps.attribution.services.attribution_validator import normalize_decimal_weights
from apps.touchpoints.models import Touchpoint


def calculate_weights(
    touchpoints: list[Touchpoint],
    *,
    conversion_cutoff: datetime | None = None,
    half_life_days: int = 7,
) -> list[Decimal]:
    """Assign equal credit 1/N across all eligible touchpoints summing strictly to 1.000000."""
    n = len(touchpoints)
    if n == 0:
        return []
    return normalize_decimal_weights([Decimal('1')] * n, anchor_index=n - 1)

