"""Serializers for Stage 9 ROI, Revenue, Creative, Audience, Funnel, Trends, and Dashboard APIs."""

from rest_framework import serializers

from apps.attribution.models import AttributionModel


class AnalyticsFilterQuerySerializer(serializers.Serializer):
    """Validated query parameters shared across all ROI & Marketing Analytics endpoints."""

    model_id = serializers.ChoiceField(
        choices=AttributionModel.ModelCode.choices,
        required=False,
        default=AttributionModel.ModelCode.POSITION_BASED,
    )
    conversion_window_days = serializers.IntegerField(
        required=False,
        default=90,
        min_value=1,
        max_value=365,
    )
    half_life_days = serializers.IntegerField(
        required=False,
        default=7,
        min_value=1,
        max_value=90,
    )
    date_range = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        default='all_time',
    )
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    campaign_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')
    channel_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')

    def validate(self, attrs):
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        if date_from and date_to and date_to < date_from:
            raise serializers.ValidationError({'date_to': ['date_to must be on or after date_from.']})
        return attrs


class AnalyticsSummarySerializer(serializers.Serializer):
    """Overall platform or filtered-scope KPIs separating revenue, spend, and pipeline."""

    model_id = serializers.CharField()
    model_name = serializers.CharField()
    period_label = serializers.CharField()
    marketing_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    actual_closed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    pipeline_value = serializers.DecimalField(max_digits=16, decimal_places=2)
    won_pipeline_value = serializers.DecimalField(max_digits=16, decimal_places=2)
    conversion_value = serializers.DecimalField(max_digits=16, decimal_places=2)
    duplicate_revenue_excluded = serializers.DecimalField(max_digits=16, decimal_places=2)
    roi = serializers.FloatField(allow_null=True)
    roas = serializers.FloatField(allow_null=True)
    cpl = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    conversion_rate = serializers.FloatField()
    aov = serializers.DecimalField(max_digits=14, decimal_places=2)
    valid_orders_count = serializers.IntegerField()
    excluded_duplicate_orders = serializers.IntegerField()
    total_campaigns = serializers.IntegerField()
    total_contacts = serializers.IntegerField()
    total_touchpoints = serializers.IntegerField()
    total_leads = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    total_opportunities = serializers.IntegerField()
    won_opportunities = serializers.IntegerField()
    currency_mismatches_count = serializers.IntegerField()
    mismatched_spend_by_currency = serializers.DictField(
        child=serializers.DecimalField(max_digits=16, decimal_places=2)
    )
    missing_cost_campaigns_count = serializers.IntegerField()


class CampaignRoiRowSerializer(serializers.Serializer):
    """Per-campaign ROI, ROAS, CPL, pipeline, attribution, and cost-alert row."""

    campaign_id = serializers.CharField()
    name = serializers.CharField()
    channel_id = serializers.CharField()
    channel_name = serializers.CharField()
    status = serializers.CharField()
    currency = serializers.CharField()
    budget = serializers.DecimalField(max_digits=14, decimal_places=2)
    is_paid_campaign = serializers.BooleanField()
    marketing_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    pipeline_value = serializers.DecimalField(max_digits=16, decimal_places=2)
    roi = serializers.FloatField(allow_null=True)
    roas = serializers.FloatField(allow_null=True)
    cpl = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    conversion_rate = serializers.FloatField()
    conversions = serializers.IntegerField()
    touchpoints = serializers.IntegerField()
    leads = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    has_currency_mismatch = serializers.BooleanField()
    mismatched_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    missing_cost_alert = serializers.BooleanField()


class ChannelRoiRowSerializer(serializers.Serializer):
    """Per-channel ROI, spend, leads, attributed revenue, and share row."""

    channel_id = serializers.CharField()
    name = serializers.CharField()
    channel_type = serializers.CharField()
    status = serializers.CharField()
    campaigns_count = serializers.IntegerField()
    marketing_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    roi = serializers.FloatField(allow_null=True)
    roas = serializers.FloatField(allow_null=True)
    cpl = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    conversion_rate = serializers.FloatField()
    leads = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    conversions = serializers.IntegerField()
    touchpoints = serializers.IntegerField()
    revenue_share_percent = serializers.FloatField()


class CostVsRevenueRowSerializer(serializers.Serializer):
    """Campaign spend vs attributed revenue comparison item formatted for Recharts."""

    campaign_id = serializers.CharField()
    name = serializers.CharField()
    channel_name = serializers.CharField()
    spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    net_return = serializers.DecimalField(max_digits=16, decimal_places=2)
    roi = serializers.FloatField(allow_null=True)


class RoiAnalyticsResponseSerializer(serializers.Serializer):
    """Combined ROI, ROAS, CPL, Conversion Rate, AOV, and Campaign/Channel breakdown payload."""

    summary = AnalyticsSummarySerializer()
    campaign_rows = CampaignRoiRowSerializer(many=True)
    channel_rows = ChannelRoiRowSerializer(many=True)
    best_campaigns = CampaignRoiRowSerializer(many=True)
    lowest_campaigns = CampaignRoiRowSerializer(many=True)
    cost_vs_revenue = CostVsRevenueRowSerializer(many=True)


class CreativePerformanceRowSerializer(serializers.Serializer):
    """Attributed revenue, touchpoint volume, and unique contacts per Creative."""

    creative_id = serializers.CharField()
    name = serializers.CharField()
    creative_type = serializers.CharField()
    status = serializers.CharField()
    primary_campaign_id = serializers.CharField(allow_null=True)
    primary_campaign_name = serializers.CharField(allow_null=True)
    campaigns_count = serializers.IntegerField()
    touchpoints = serializers.IntegerField()
    unique_contacts = serializers.IntegerField()
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    conversions = serializers.IntegerField()
    revenue_share_percent = serializers.FloatField()


class AudiencePerformanceRowSerializer(serializers.Serializer):
    """Rolled-up ROI, leads, and attributed revenue per Audience segment."""

    audience_id = serializers.CharField()
    name = serializers.CharField()
    audience_type = serializers.CharField()
    status = serializers.CharField()
    estimated_size = serializers.IntegerField()
    campaigns_count = serializers.IntegerField()
    marketing_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    roi = serializers.FloatField(allow_null=True)
    roas = serializers.FloatField(allow_null=True)
    cpl = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    conversion_rate = serializers.FloatField()
    leads = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    conversions = serializers.IntegerField()
    touchpoints = serializers.IntegerField()


class MonthlyTrendRowSerializer(serializers.Serializer):
    """Monthly Recharts time-series bucket comparing spend, closed revenue, and attributed revenue."""

    month_key = serializers.CharField()
    month = serializers.CharField()
    spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    closed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    orders_count = serializers.IntegerField()
    leads_count = serializers.IntegerField()
    roi = serializers.FloatField(allow_null=True)
    roas = serializers.FloatField(allow_null=True)
    cumulative_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    cumulative_closed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    cumulative_attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)


class TrendsResponseSerializer(serializers.Serializer):
    """Monthly time-series trend payload plus Pandas/NumPy statistical summary."""

    model_id = serializers.CharField()
    period_label = serializers.CharField()
    monthly_series = MonthlyTrendRowSerializer(many=True)
    statistics = serializers.DictField()


class FunnelAnalyticsResponseSerializer(serializers.Serializer):
    """Lead lifecycle and 6-stage Opportunity pipeline conversion analytics payload."""

    model_id = serializers.CharField()
    period_label = serializers.CharField()
    funnel_stages = serializers.ListField(child=serializers.DictField())
    lead_summary = serializers.DictField()
    opportunity_summary = serializers.DictField()


class CampaignAnalyticsResponseSerializer(serializers.Serializer):
    """Ranked campaign ROI & Spend-vs-Revenue comparison response."""

    summary = AnalyticsSummarySerializer()
    campaigns = CampaignRoiRowSerializer(many=True)
    best_campaigns = CampaignRoiRowSerializer(many=True)
    lowest_campaigns = CampaignRoiRowSerializer(many=True)
    cost_vs_revenue = CostVsRevenueRowSerializer(many=True)


class ChannelAnalyticsResponseSerializer(serializers.Serializer):
    """Channel-wise ROI and spend-vs-revenue response."""

    summary = AnalyticsSummarySerializer()
    channels = ChannelRoiRowSerializer(many=True)


class CreativeAnalyticsResponseSerializer(serializers.Serializer):
    """Creative performance leaderboard response."""

    model_id = serializers.CharField()
    period_label = serializers.CharField()
    total_creative_attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    creatives = CreativePerformanceRowSerializer(many=True)


class AudienceAnalyticsResponseSerializer(serializers.Serializer):
    """Audience segment performance response."""

    model_id = serializers.CharField()
    period_label = serializers.CharField()
    audiences = AudiencePerformanceRowSerializer(many=True)


class DashboardAnalyticsResponseSerializer(serializers.Serializer):
    """Executive Dashboard payload combining KPI cards, Recharts charts, and widgets."""

    kpis = AnalyticsSummarySerializer()
    charts = serializers.DictField()
    trend_statistics = serializers.DictField()
    widgets = serializers.DictField()
