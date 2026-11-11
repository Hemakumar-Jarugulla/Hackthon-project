"""DRF API views exposing ROI, Campaign/Channel/Creative/Audience performance, Funnel, Trends, and Dashboard."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.analytics.serializers import (
    AnalyticsFilterQuerySerializer,
    AudienceAnalyticsResponseSerializer,
    CampaignAnalyticsResponseSerializer,
    ChannelAnalyticsResponseSerializer,
    CreativeAnalyticsResponseSerializer,
    DashboardAnalyticsResponseSerializer,
    FunnelAnalyticsResponseSerializer,
    RoiAnalyticsResponseSerializer,
    TrendsResponseSerializer,
)
from apps.analytics.services.dashboard import build_dashboard_analytics
from apps.analytics.services.metrics import ZERO_MONEY, quantize_money
from apps.analytics.services.roi_analytics import (
    aggregate_campaigns_and_channels,
    build_analytics_context,
    build_audience_performance,
    build_creative_performance,
    build_roi_analytics,
    build_summary_kpis,
)
from apps.analytics.services.trends import build_funnel_analytics, build_monthly_trends
from common.permissions import IsActiveUser
from common.responses import success_response

ANALYTICS_OPENAPI_PARAMETERS = [
    OpenApiParameter('model_id', str, required=False, description='Attribution model code'),
    OpenApiParameter('conversion_window_days', int, required=False),
    OpenApiParameter('half_life_days', int, required=False),
    OpenApiParameter('date_range', str, required=False),
    OpenApiParameter('date_from', str, required=False),
    OpenApiParameter('date_to', str, required=False),
    OpenApiParameter('campaign_id', str, required=False),
    OpenApiParameter('channel_id', str, required=False),
]


def _extract_analytics_query_params(request) -> dict:
    """Normalize snake_case and camelCase query filters consistently."""
    qp = request.query_params
    payload: dict = {}
    aliases = (
        ('model_id', 'modelId'),
        ('conversion_window_days', 'conversionWindowDays'),
        ('half_life_days', 'halfLifeDays'),
        ('date_range', 'dateRange'),
        ('date_from', 'dateFrom'),
        ('date_to', 'dateTo'),
        ('campaign_id', 'campaignId'),
        ('channel_id', 'channelId'),
    )
    for snake_key, camel_key in aliases:
        if snake_key in qp or camel_key in qp:
            val = qp.get(snake_key) if snake_key in qp else qp.get(camel_key)
            if val not in (None, ''):
                payload[snake_key] = val
    return payload


class BaseAnalyticsAPIView(APIView):
    """Shared authenticated read-only base class handling analytics query validation."""

    permission_classes = [IsActiveUser]

    def get_validated_filters(self, request) -> dict:
        raw = _extract_analytics_query_params(request)
        serializer = AnalyticsFilterQuerySerializer(data=raw)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class RoiAnalyticsView(BaseAnalyticsAPIView):
    """Overall ROI, ROAS, CPL, Conversion Rate, AOV, and ranked Campaign/Channel breakdown."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Overall ROI, ROAS, CPL, AOV & Spend Analytics',
        parameters=ANALYTICS_OPENAPI_PARAMETERS,
        responses={200: RoiAnalyticsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        payload = build_roi_analytics(**filters)
        out = RoiAnalyticsResponseSerializer(payload)
        return success_response(
            data=out.data,
            message='ROI analytics computed successfully.',
        )


class CampaignAnalyticsView(BaseAnalyticsAPIView):
    """Campaign-wise ROI ranking and Spend vs Attributed Revenue comparison."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Campaign ROI Performance & Ranking',
        parameters=[
            *ANALYTICS_OPENAPI_PARAMETERS,
            OpenApiParameter(
                'ordering',
                str,
                required=False,
                description='Sort key: roi, -roi, attributed_revenue, -attributed_revenue, spend, -spend, leads, -leads',
            ),
        ],
        responses={200: CampaignAnalyticsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        payload = build_roi_analytics(**filters)
        ordering = (request.query_params.get('ordering') or '-roi').strip()
        reverse = ordering.startswith('-')
        sort_field = ordering.lstrip('-')
        key_map = {
            'roi': lambda r: (r['roi'] is not None, r['roi'] or 0.0, r['attributed_revenue']),
            'attributed_revenue': lambda r: r['attributed_revenue'],
            'spend': lambda r: r['marketing_spend'],
            'leads': lambda r: r['leads'],
            'roas': lambda r: (r['roas'] is not None, r['roas'] or 0.0),
            'conversions': lambda r: r['conversions'],
        }
        if sort_field in key_map:
            payload['campaign_rows'] = sorted(
                payload['campaign_rows'],
                key=key_map[sort_field],
                reverse=reverse,
            )

        out = CampaignAnalyticsResponseSerializer(
            {
                'summary': payload['summary'],
                'campaigns': payload['campaign_rows'],
                'best_campaigns': payload['best_campaigns'],
                'lowest_campaigns': payload['lowest_campaigns'],
                'cost_vs_revenue': payload['cost_vs_revenue'],
            }
        )
        return success_response(
            data=out.data,
            message='Campaign performance analytics retrieved.',
        )


class ChannelAnalyticsView(BaseAnalyticsAPIView):
    """Channel-wise ROI, ROAS, CPL, leads, conversions, and attributed revenue share."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Channel-Wise ROI & Revenue Share',
        parameters=ANALYTICS_OPENAPI_PARAMETERS,
        responses={200: ChannelAnalyticsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        ctx = build_analytics_context(**filters)
        campaign_rows, channel_rows = aggregate_campaigns_and_channels(ctx)
        summary = build_summary_kpis(ctx, campaign_rows)
        out = ChannelAnalyticsResponseSerializer(
            {
                'summary': summary,
                'channels': channel_rows,
            }
        )
        return success_response(
            data=out.data,
            message='Channel performance analytics retrieved.',
        )


class CreativeAnalyticsView(BaseAnalyticsAPIView):
    """Creative performance leaderboard built from touchpoint engagement & attribution credits."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Creative Performance Analytics',
        parameters=ANALYTICS_OPENAPI_PARAMETERS,
        responses={200: CreativeAnalyticsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        ctx = build_analytics_context(**filters)
        creatives = build_creative_performance(ctx)
        total_attr = quantize_money(sum((r['attributed_revenue'] for r in creatives), ZERO_MONEY))
        out = CreativeAnalyticsResponseSerializer(
            {
                'model_id': ctx['model_id'],
                'period_label': ctx['period_label'],
                'total_creative_attributed_revenue': total_attr,
                'creatives': creatives,
            }
        )
        return success_response(
            data=out.data,
            message='Creative performance analytics retrieved.',
        )


class AudienceAnalyticsView(BaseAnalyticsAPIView):
    """Audience segment ROI, leads, conversions, and attributed revenue analytics."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Audience Segment Performance Analytics',
        parameters=ANALYTICS_OPENAPI_PARAMETERS,
        responses={200: AudienceAnalyticsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        ctx = build_analytics_context(**filters)
        campaign_rows, _ = aggregate_campaigns_and_channels(ctx)
        audiences = build_audience_performance(ctx, campaign_rows)
        out = AudienceAnalyticsResponseSerializer(
            {
                'model_id': ctx['model_id'],
                'period_label': ctx['period_label'],
                'audiences': audiences,
            }
        )
        return success_response(
            data=out.data,
            message='Audience performance analytics retrieved.',
        )


class FunnelAnalyticsView(BaseAnalyticsAPIView):
    """Lead lifecycle conversion rates and 6-stage Opportunity pipeline analytics."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Lead & Opportunity Conversion Funnel Analytics',
        parameters=ANALYTICS_OPENAPI_PARAMETERS,
        responses={200: FunnelAnalyticsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        ctx = build_analytics_context(**filters)
        funnel = build_funnel_analytics(ctx)
        out = FunnelAnalyticsResponseSerializer(funnel)
        return success_response(
            data=out.data,
            message='Funnel analytics retrieved.',
        )


class TrendsAnalyticsView(BaseAnalyticsAPIView):
    """Monthly marketing spend, closed revenue, attributed revenue, ROI trends & statistics."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Monthly Spend & Revenue Trends',
        parameters=ANALYTICS_OPENAPI_PARAMETERS,
        responses={200: TrendsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        ctx = build_analytics_context(**filters)
        trends = build_monthly_trends(ctx)
        out = TrendsResponseSerializer(
            {
                'model_id': ctx['model_id'],
                'period_label': ctx['period_label'],
                'monthly_series': trends['monthly_series'],
                'statistics': trends['statistics'],
            }
        )
        return success_response(
            data=out.data,
            message='Monthly revenue and spend trends retrieved.',
        )


class DashboardAnalyticsView(BaseAnalyticsAPIView):
    """Unified Executive Dashboard payload returning KPIs, 9 Recharts series, and operational widgets."""

    @extend_schema(
        tags=['Analytics'],
        summary='Get Unified Executive Dashboard Analytics',
        parameters=ANALYTICS_OPENAPI_PARAMETERS,
        responses={200: DashboardAnalyticsResponseSerializer},
    )
    def get(self, request):
        filters = self.get_validated_filters(request)
        dashboard = build_dashboard_analytics(**filters)
        out = DashboardAnalyticsResponseSerializer(dashboard)
        return success_response(
            data=out.data,
            message='Dashboard analytics retrieved.',
        )
