"""Analytics calculation services package."""

from apps.analytics.services.dashboard import build_dashboard_analytics
from apps.analytics.services.metrics import (
    calculate_aov,
    calculate_conversion_rate,
    calculate_cpl,
    calculate_roas,
    calculate_roi,
)
from apps.analytics.services.roi_analytics import (
    build_analytics_context,
    build_audience_performance,
    build_creative_performance,
    build_roi_analytics,
)
from apps.analytics.services.trends import build_funnel_analytics, build_monthly_trends

__all__ = [
    'build_analytics_context',
    'build_audience_performance',
    'build_creative_performance',
    'build_dashboard_analytics',
    'build_funnel_analytics',
    'build_monthly_trends',
    'build_roi_analytics',
    'calculate_aov',
    'calculate_conversion_rate',
    'calculate_cpl',
    'calculate_roas',
    'calculate_roi',
]

