"""URL routes for ROI & Marketing Analytics endpoints."""

from django.urls import path

from apps.analytics.views import (
    AudienceAnalyticsView,
    CampaignAnalyticsView,
    ChannelAnalyticsView,
    CreativeAnalyticsView,
    DashboardAnalyticsView,
    FunnelAnalyticsView,
    RoiAnalyticsView,
    TrendsAnalyticsView,
)

urlpatterns = [
    path('overview/', RoiAnalyticsView.as_view(), name='analytics-overview'),
    path('roi/', RoiAnalyticsView.as_view(), name='analytics-roi'),
    path('campaigns/', CampaignAnalyticsView.as_view(), name='analytics-campaigns'),
    path('campaign-performance/', CampaignAnalyticsView.as_view(), name='analytics-campaign-performance'),
    path('channels/', ChannelAnalyticsView.as_view(), name='analytics-channels'),
    path('channel-performance/', ChannelAnalyticsView.as_view(), name='analytics-channel-performance'),
    path('creatives/', CreativeAnalyticsView.as_view(), name='analytics-creatives'),
    path('audiences/', AudienceAnalyticsView.as_view(), name='analytics-audiences'),
    path('funnel/', FunnelAnalyticsView.as_view(), name='analytics-funnel'),
    path('conversion-funnel/', FunnelAnalyticsView.as_view(), name='analytics-conversion-funnel'),
    path('trends/', TrendsAnalyticsView.as_view(), name='analytics-trends'),
    path('revenue-trends/', TrendsAnalyticsView.as_view(), name='analytics-revenue-trends'),
    path('dashboard/', DashboardAnalyticsView.as_view(), name='analytics-dashboard'),
]

