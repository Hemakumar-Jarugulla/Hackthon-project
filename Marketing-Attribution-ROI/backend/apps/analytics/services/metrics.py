"""
Safe financial KPI calculation helpers for ROI & Marketing Analytics.

Implements zero-spend, zero-denominator, and missing-cost protection on top of
`common.utils.safe_divide` so division by zero never occurs across API endpoints.
"""

from decimal import Decimal, ROUND_HALF_UP

from common.utils import safe_divide

CURRENCY_QUANTUM = Decimal('0.01')
ZERO_MONEY = Decimal('0.00')


def quantize_money(value: Decimal | int | float | None) -> Decimal:
    """Quantize a monetary figure cleanly to 2 decimal places."""
    if value is None:
        return ZERO_MONEY
    return Decimal(str(value)).quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_roi(
    attributed_revenue: Decimal | float | int | None,
    marketing_cost: Decimal | float | int | None,
) -> float | None:
    """
    ROI = ((Attributed Revenue - Marketing Cost) / Marketing Cost) * 100.
    Returns None when marketing_cost is zero, negative, or missing.
    """
    if marketing_cost is None:
        return None
    cost = Decimal(str(marketing_cost))
    if cost <= 0:
        return None
    rev = Decimal(str(attributed_revenue or 0))
    ratio = safe_divide((rev - cost) * Decimal('100'), cost, default=None)
    return round(float(ratio), 2) if ratio is not None else None


def calculate_roas(
    attributed_revenue: Decimal | float | int | None,
    marketing_cost: Decimal | float | int | None,
) -> float | None:
    """
    ROAS = Attributed Revenue / Marketing Cost.
    Returns None when marketing_cost is zero, negative, or missing.
    """
    if marketing_cost is None:
        return None
    cost = Decimal(str(marketing_cost))
    if cost <= 0:
        return None
    rev = Decimal(str(attributed_revenue or 0))
    ratio = safe_divide(rev, cost, default=None)
    return round(float(ratio), 2) if ratio is not None else None


def calculate_cpl(
    marketing_cost: Decimal | float | int | None,
    total_leads: int | None,
) -> Decimal | None:
    """
    CPL = Marketing Cost / Number of Leads.
    Returns None when total_leads is zero/missing or marketing_cost is None.
    """
    if marketing_cost is None or total_leads is None or int(total_leads) <= 0:
        return None
    cost = Decimal(str(marketing_cost))
    if cost < 0:
        return None
    val = safe_divide(cost, int(total_leads), default=None)
    return val.quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP) if val is not None else None


def calculate_conversion_rate(
    converted_leads: int | None,
    total_leads: int | None,
) -> float:
    """Conversion Rate = (Converted Leads / Total Leads) * 100, returning 0.0 when no leads."""
    if not total_leads or int(total_leads) <= 0:
        return 0.0
    converted = max(0, int(converted_leads or 0))
    ratio = safe_divide(Decimal(converted) * Decimal('100'), int(total_leads), default=Decimal('0'))
    return round(float(ratio), 2)


def calculate_aov(
    total_closed_revenue: Decimal | float | int | None,
    valid_orders_count: int | None,
) -> Decimal:
    """AOV = Total Closed Revenue / Valid Orders, returning Decimal('0.00') when zero orders."""
    if not valid_orders_count or int(valid_orders_count) <= 0:
        return ZERO_MONEY
    closed = Decimal(str(total_closed_revenue or 0))
    val = safe_divide(closed, int(valid_orders_count), default=ZERO_MONEY)
    return val.quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)


def build_unit_economics(
    *,
    attributed_revenue: Decimal,
    marketing_spend: Decimal,
    total_leads: int,
    converted_leads: int,
) -> dict:
    """Compute unified ROI, ROAS, CPL, and conversion_rate metrics for any aggregation entity."""
    rev = quantize_money(attributed_revenue)
    spend = quantize_money(marketing_spend)
    return {
        'marketing_spend': spend,
        'attributed_revenue': rev,
        'roi': calculate_roi(rev, spend),
        'roas': calculate_roas(rev, spend),
        'cpl': calculate_cpl(spend, total_leads),
        'conversion_rate': calculate_conversion_rate(converted_leads, total_leads),
    }

