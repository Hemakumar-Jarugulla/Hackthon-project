"""Last-Touch attribution model calculator (100% credit to final pre-conversion touch)."""

from datetime import datetime
from decimal import Decimal

from apps.attribution.services.attribution_validator import WEIGHT_TOTAL, ZERO_WEIGHT
from apps.touchpoints.models import Touchpoint


def calculate_weights(
    touchpoints: list[Touchpoint],
    *,
    conversion_cutoff: datetime | None = None,
    half_life_days: int = 7,
) -> list[Decimal]:
    """Assign 1.000000 credit to the final touchpoint (index -1) and 0.000000 to earlier ones."""
    n = len(touchpoints)
    if n == 0:
        return []
    return [WEIGHT_TOTAL if idx == n - 1 else ZERO_WEIGHT for idx in range(n)]

