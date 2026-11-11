"""
Unified Executive Dashboard analytics aggregator producing KPI cards,
Recharts visualization series, and recent operational activity widgets.
"""

from apps.analytics.services.metrics import ZERO_MONEY, quantize_money
from apps.analytics.services.roi_analytics import (
    aggregate_campaigns_and_channels,
    build_analytics_context,
    build_audience_performance,
    build_creative_performance,
    build_summary_kpis,
)
from apps.analytics.services.trends import build_funnel_analytics, build_monthly_trends
from apps.attribution.models import AttributionRun
from apps.contacts.models import Contact
from apps.exceptions.models import DataException


def build_dashboard_analytics(**filters) -> dict:
    """Assemble full Executive Dashboard KPIs, charts, and operational widgets."""
    ctx = build_analytics_context(**filters)
    campaign_rows, channel_rows = aggregate_campaigns_and_channels(ctx)
    summary = build_summary_kpis(ctx, campaign_rows)
    trends = build_monthly_trends(ctx)
    funnel = build_funnel_analytics(ctx)
    creative_rows = build_creative_performance(ctx)
    audience_rows = build_audience_performance(ctx, campaign_rows)

    campaign_roi_ranking = [
        {
            'campaign_id': row['campaign_id'],
            'name': f"{row['name'][:22]}..." if len(row['name']) > 22 else row['name'],
            'full_name': row['name'],
            'roi': row['roi'],
            'spend': row['marketing_spend'],
            'attributed_revenue': row['attributed_revenue'],
        }
        for row in campaign_rows
        if row['roi'] is not None
    ]

    channel_performance = [
        {
            'channel_id': row['channel_id'],
            'channel': row['name'],
            'channel_type': row['channel_type'],
            'spend': row['marketing_spend'],
            'attributed_revenue': row['attributed_revenue'],
            'leads': row['leads'],
            'roi': row['roi'],
        }
        for row in channel_rows
    ]

    model_distribution = [
        {
            'name': row['name'],
            'value': row['attributed_revenue'],
            'share_percent': row['revenue_share_percent'],
        }
        for row in channel_rows
        if row['attributed_revenue'] > ZERO_MONEY
    ]

    # Contact journey touchpoint depth distribution across all active contacts
    valid_touches_by_contact: dict[str, int] = {}
    for tp in ctx['touchpoints']:
        if tp.is_valid:
            valid_touches_by_contact[tp.contact_id] = valid_touches_by_contact.get(tp.contact_id, 0) + 1

    all_contact_ids = list(Contact.objects.values_list('id', flat=True))
    journey_buckets = {'1 Touch': 0, '2 Touches': 0, '3 Touches': 0, '4+ Touches': 0}
    for cid in all_contact_ids:
        cnt = valid_touches_by_contact.get(cid, 0)
        if cnt <= 1:
            journey_buckets['1 Touch'] += 1
        elif cnt == 2:
            journey_buckets['2 Touches'] += 1
        elif cnt == 3:
            journey_buckets['3 Touches'] += 1
        else:
            journey_buckets['4+ Touches'] += 1
    journey_distribution = [
        {'bucket': bucket, 'contacts': count} for bucket, count in journey_buckets.items()
    ]

    all_exceptions = list(DataException.objects.all().order_by('-created_at', 'id'))
    exc_by_severity = {sev.value: 0 for sev in DataException.Severity}
    for exc in all_exceptions:
        if exc.severity in exc_by_severity:
            exc_by_severity[exc.severity] += 1
    exception_distribution = [
        {'severity': sev, 'count': cnt} for sev, cnt in exc_by_severity.items()
    ]

    top_campaigns = sorted(
        campaign_rows,
        key=lambda r: (r['attributed_revenue'], r['conversions']),
        reverse=True,
    )[:5]

    recent_leads = [
        {
            'id': lead.id,
            'contact_id': lead.contact_id,
            'contact_name': lead.contact.name if lead.contact else lead.contact_id,
            'campaign_id': lead.campaign_id,
            'source': lead.source,
            'score': lead.score,
            'status': lead.status,
            'created_date': lead.created_date,
        }
        for lead in sorted(ctx['leads'], key=lambda x: (x.created_date, x.id), reverse=True)[:5]
    ]

    recent_opportunities = [
        {
            'id': opp.id,
            'name': opp.name,
            'stage': opp.stage,
            'status': opp.status,
            'expected_revenue': quantize_money(opp.expected_revenue),
            'actual_revenue': quantize_money(opp.actual_revenue),
            'closing_date': opp.closing_date,
        }
        for opp in sorted(
            ctx['opportunities'],
            key=lambda x: (x.closing_date, x.id),
            reverse=True,
        )[:5]
    ]

    recent_touchpoints = [
        {
            'id': tp.id,
            'contact_id': tp.contact_id,
            'campaign_id': tp.campaign_id,
            'channel_id': tp.channel_id,
            'interaction_type': tp.interaction_type,
            'timestamp': tp.timestamp,
            'is_online': tp.is_online,
        }
        for tp in sorted(ctx['touchpoints'], key=lambda x: (x.timestamp, x.id), reverse=True)[:5]
    ]

    recent_runs = [
        {
            'id': run.id,
            'attribution_model': run.attribution_model_id,
            'model_name': run.attribution_model.name,
            'period_label': run.period_label,
            'conversion_window_days': run.conversion_window_days,
            'valid_orders_processed': run.valid_orders_processed,
            'total_attributed_revenue': quantize_money(run.total_attributed_revenue),
            'executed_at': run.executed_at,
        }
        for run in AttributionRun.objects.select_related('attribution_model')
        .order_by('-executed_at', 'id')[:4]
    ]

    data_quality_alerts = [
        {
            'id': exc.id,
            'issue_type': exc.issue_type,
            'entity_type': exc.entity_type,
            'entity_id': exc.entity_id,
            'severity': exc.severity,
            'resolution_status': exc.resolution_status,
            'description': exc.description,
        }
        for exc in all_exceptions[:5]
    ]

    return {
        'kpis': summary,
        'charts': {
            'monthly_series': trends['monthly_series'],
            'campaign_roi_ranking': campaign_roi_ranking,
            'channel_performance': channel_performance,
            'funnel_data': funnel['funnel_stages'],
            'model_distribution': model_distribution,
            'journey_distribution': journey_distribution,
            'exception_distribution': exception_distribution,
            'creative_performance': creative_rows[:10],
            'audience_performance': audience_rows[:10],
        },
        'trend_statistics': trends['statistics'],
        'widgets': {
            'top_campaigns': top_campaigns,
            'recent_leads': recent_leads,
            'recent_opportunities': recent_opportunities,
            'data_quality_alerts': data_quality_alerts,
            'recent_attribution_runs': recent_runs,
            'recent_touchpoints': recent_touchpoints,
        },
    }
