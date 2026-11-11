"""
Core ROI & Performance Analytics services across Overall Summary, Campaigns,
Channels, Creatives, and Audiences using reconciled attribution & verified cost ledgers.
"""

from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

from apps.analytics.services.metrics import (
    ZERO_MONEY,
    build_unit_economics,
    calculate_aov,
    quantize_money,
)
from apps.attribution.services.attribution_engine import (
    execute_attribution_run,
    resolve_date_bounds,
)
from apps.audiences.models import Audience
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint


def _normalize_optional_filter(value: str | None) -> str | None:
    cleaned = (value or '').strip()
    if not cleaned or cleaned.lower() == 'all':
        return None
    return cleaned


def build_analytics_context(
    *,
    model_id: str | None = None,
    conversion_window_days: int | None = None,
    half_life_days: int | None = None,
    date_range: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    campaign_id: str | None = None,
    channel_id: str | None = None,
) -> dict:
    """
    Assemble a single coherent, query-efficient analytics dataset scoped by date bounds,
    attribution model, campaign, and channel filters.
    """
    campaign_filter = _normalize_optional_filter(campaign_id)
    channel_filter = _normalize_optional_filter(channel_id)
    bound_start, bound_end, period_label = resolve_date_bounds(
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )

    # Always run multi-touch attribution over full customer journeys in the date window
    # before slicing credits to any single campaign/channel filter.
    attr_run = execute_attribution_run(
        model_id=model_id,
        conversion_window_days=conversion_window_days,
        half_life_days=half_life_days,
        date_range=date_range,
        date_from=bound_start,
        date_to=bound_end,
        persist=False,
    )

    all_channels = list(Channel.objects.all().order_by('id'))
    all_campaigns = list(Campaign.objects.select_related('channel').order_by('id'))
    channel_map = {ch.id: ch for ch in all_channels}
    campaign_map = {c.id: c for c in all_campaigns}

    scoped_channels = [
        ch for ch in all_channels if channel_filter is None or ch.id == channel_filter
    ]
    scoped_campaigns = [
        c
        for c in all_campaigns
        if (campaign_filter is None or c.id == campaign_filter)
        and (channel_filter is None or c.channel_id == channel_filter)
    ]
    active_campaign_ids = {c.id for c in scoped_campaigns}
    is_scoped = bool(campaign_filter or channel_filter)

    costs_qs = CostRecord.objects.select_related('campaign', 'channel').order_by('spend_date', 'id')
    orders_qs = Order.objects.select_related(
        'contact',
        'opportunity',
        'opportunity__lead',
    ).order_by('order_date', 'id')
    leads_qs = Lead.objects.select_related('campaign', 'contact').order_by('created_date', 'id')
    opps_qs = Opportunity.objects.select_related('lead', 'contact').order_by('closing_date', 'id')
    tp_qs = Touchpoint.objects.select_related('campaign', 'channel', 'creative').order_by(
        'timestamp', 'id'
    )

    if bound_start is not None:
        costs_qs = costs_qs.filter(spend_date__gte=bound_start)
        orders_qs = orders_qs.filter(order_date__gte=bound_start)
        leads_qs = leads_qs.filter(created_date__gte=bound_start)
        opps_qs = opps_qs.filter(closing_date__gte=bound_start)
        tp_qs = tp_qs.filter(
            timestamp__gte=datetime(
                bound_start.year, bound_start.month, bound_start.day, 0, 0, 0, tzinfo=dt_timezone.utc
            )
        )
    if bound_end is not None:
        costs_qs = costs_qs.filter(spend_date__lte=bound_end)
        orders_qs = orders_qs.filter(order_date__lte=bound_end)
        leads_qs = leads_qs.filter(created_date__lte=bound_end)
        opps_qs = opps_qs.filter(closing_date__lte=bound_end)
        tp_qs = tp_qs.filter(
            timestamp__lte=datetime(
                bound_end.year, bound_end.month, bound_end.day, 23, 59, 59, tzinfo=dt_timezone.utc
            )
        )

    if is_scoped:
        costs_qs = costs_qs.filter(campaign_id__in=active_campaign_ids)
        leads_qs = leads_qs.filter(campaign_id__in=active_campaign_ids)
        opps_qs = opps_qs.filter(lead__campaign_id__in=active_campaign_ids)
        orders_qs = orders_qs.filter(opportunity__lead__campaign_id__in=active_campaign_ids)
        if channel_filter and not campaign_filter:
            tp_qs = tp_qs.filter(channel_id=channel_filter)
        else:
            tp_qs = tp_qs.filter(campaign_id__in=active_campaign_ids)

    costs = list(costs_qs)
    orders = list(orders_qs)
    leads = list(leads_qs)
    opportunities = list(opps_qs)
    touchpoints = list(tp_qs)

    if is_scoped:
        order_credits = [
            cr
            for cr in attr_run['order_credits']
            if (campaign_filter and cr['campaign_id'] == campaign_filter)
            or (
                not campaign_filter
                and (
                    cr['channel_id'] == channel_filter
                    or cr['campaign_id'] in active_campaign_ids
                )
            )
        ]
    else:
        order_credits = list(attr_run['order_credits'])

    valid_paid_orders = [
        o
        for o in orders
        if o.verification_status == Order.VerificationStatus.VALID
        and o.payment_status == Order.PaymentStatus.PAID
    ]
    duplicate_orders = [
        o for o in orders if o.verification_status == Order.VerificationStatus.DUPLICATE
    ]

    matched_costs: list[CostRecord] = []
    mismatched_costs: list[CostRecord] = []
    for cost in costs:
        if cost.currency == cost.campaign.currency:
            matched_costs.append(cost)
        else:
            mismatched_costs.append(cost)

    return {
        'model_id': attr_run['model_id'],
        'model_name': attr_run['model_name'],
        'rule_version': attr_run['rule_version'],
        'period_label': period_label,
        'conversion_window_days': attr_run['conversion_window_days'],
        'half_life_days': attr_run['half_life_days'],
        'campaign_filter': campaign_filter,
        'channel_filter': channel_filter,
        'is_scoped': is_scoped,
        'all_channels': all_channels,
        'all_campaigns': all_campaigns,
        'channel_map': channel_map,
        'campaign_map': campaign_map,
        'scoped_channels': scoped_channels,
        'scoped_campaigns': scoped_campaigns,
        'matched_costs': matched_costs,
        'mismatched_costs': mismatched_costs,
        'orders': orders,
        'valid_paid_orders': valid_paid_orders,
        'duplicate_orders': duplicate_orders,
        'leads': leads,
        'opportunities': opportunities,
        'touchpoints': touchpoints,
        'order_credits': order_credits,
        'attr_run': attr_run,
    }


def aggregate_campaigns_and_channels(ctx: dict) -> tuple[list[dict], list[dict]]:
    """Aggregate matched spend, leads, pipeline, touchpoints, and attributed revenue per Campaign and Channel."""
    scoped_campaigns: list[Campaign] = ctx['scoped_campaigns']
    scoped_channels: list[Channel] = ctx['scoped_channels']
    channel_map: dict[str, Channel] = ctx['channel_map']

    cmp_spend: dict[str, Decimal] = {c.id: ZERO_MONEY for c in scoped_campaigns}
    cmp_mismatch: dict[str, bool] = {c.id: False for c in scoped_campaigns}
    cmp_mismatch_spend: dict[str, Decimal] = {c.id: ZERO_MONEY for c in scoped_campaigns}
    cmp_leads: dict[str, int] = {c.id: 0 for c in scoped_campaigns}
    cmp_converted_leads: dict[str, int] = {c.id: 0 for c in scoped_campaigns}
    cmp_pipeline: dict[str, Decimal] = {c.id: ZERO_MONEY for c in scoped_campaigns}
    cmp_touches: dict[str, int] = {c.id: 0 for c in scoped_campaigns}
    cmp_attr_rev: dict[str, Decimal] = {c.id: ZERO_MONEY for c in scoped_campaigns}
    cmp_conv_orders: dict[str, set[str]] = {c.id: set() for c in scoped_campaigns}

    ch_direct_attr_rev: dict[str, Decimal] = {ch.id: ZERO_MONEY for ch in scoped_channels}
    ch_conv_orders: dict[str, set[str]] = {ch.id: set() for ch in scoped_channels}
    ch_direct_touches: dict[str, int] = {ch.id: 0 for ch in scoped_channels}

    for cost in ctx['matched_costs']:
        if cost.campaign_id in cmp_spend:
            cmp_spend[cost.campaign_id] += cost.amount
    for cost in ctx['mismatched_costs']:
        if cost.campaign_id in cmp_mismatch:
            cmp_mismatch[cost.campaign_id] = True
            cmp_mismatch_spend[cost.campaign_id] += cost.amount

    for lead in ctx['leads']:
        cid = lead.campaign_id
        if cid in cmp_leads:
            cmp_leads[cid] += 1
            if lead.status == Lead.Status.CONVERTED:
                cmp_converted_leads[cid] += 1

    for opp in ctx['opportunities']:
        cid = opp.lead.campaign_id if opp.lead else None
        if cid in cmp_pipeline and opp.status == Opportunity.Status.OPEN:
            cmp_pipeline[cid] += opp.expected_revenue

    for tp in ctx['touchpoints']:
        if not tp.is_valid:
            continue
        if tp.campaign_id in cmp_touches:
            cmp_touches[tp.campaign_id] += 1
        elif tp.channel_id in ch_direct_touches:
            ch_direct_touches[tp.channel_id] += 1

    for credit in ctx['order_credits']:
        cid = credit['campaign_id']
        ch_id = credit['channel_id']
        rev = Decimal(str(credit['attributed_revenue']))
        weight = Decimal(str(credit['credit_weight']))
        if cid in cmp_attr_rev:
            cmp_attr_rev[cid] += rev
            if weight > 0:
                cmp_conv_orders[cid].add(credit['order_id'])
        if ch_id in ch_direct_attr_rev:
            ch_direct_attr_rev[ch_id] += rev
            if weight > 0:
                ch_conv_orders[ch_id].add(credit['order_id'])

    campaign_rows: list[dict] = []
    for c in scoped_campaigns:
        spend = quantize_money(cmp_spend[c.id])
        attr_rev = quantize_money(cmp_attr_rev[c.id])
        leads_cnt = cmp_leads[c.id]
        conv_leads = cmp_converted_leads[c.id]
        tp_cnt = cmp_touches[c.id]
        missing_cost_alert = bool(
            c.is_paid_campaign and c.budget > 0 and spend == ZERO_MONEY and (tp_cnt > 0 or leads_cnt > 0)
        )
        unit = build_unit_economics(
            attributed_revenue=attr_rev,
            marketing_spend=spend,
            total_leads=leads_cnt,
            converted_leads=conv_leads,
        )
        ch_obj = channel_map.get(c.channel_id)
        campaign_rows.append(
            {
                'campaign_id': c.id,
                'name': c.name,
                'channel_id': c.channel_id,
                'channel_name': ch_obj.name if ch_obj else 'Unknown',
                'status': c.status,
                'currency': c.currency,
                'budget': quantize_money(c.budget),
                'is_paid_campaign': c.is_paid_campaign,
                **unit,
                'pipeline_value': quantize_money(cmp_pipeline[c.id]),
                'conversions': len(cmp_conv_orders[c.id]),
                'touchpoints': tp_cnt,
                'leads': leads_cnt,
                'converted_leads': conv_leads,
                'has_currency_mismatch': cmp_mismatch[c.id],
                'mismatched_spend': quantize_money(cmp_mismatch_spend[c.id]),
                'missing_cost_alert': missing_cost_alert,
            }
        )

    total_channel_attr = sum(ch_direct_attr_rev.values(), ZERO_MONEY)
    channel_rows: list[dict] = []
    for ch in scoped_channels:
        ch_campaigns = [row for row in campaign_rows if row['channel_id'] == ch.id]
        ch_spend = sum((row['marketing_spend'] for row in ch_campaigns), ZERO_MONEY)
        ch_attr_rev = quantize_money(ch_direct_attr_rev[ch.id])
        ch_leads = sum(row['leads'] for row in ch_campaigns)
        ch_conv_leads = sum(row['converted_leads'] for row in ch_campaigns)
        ch_touches = sum(row['touchpoints'] for row in ch_campaigns) + ch_direct_touches[ch.id]
        unit = build_unit_economics(
            attributed_revenue=ch_attr_rev,
            marketing_spend=ch_spend,
            total_leads=ch_leads,
            converted_leads=ch_conv_leads,
        )
        share = (
            round(float(ch_attr_rev / total_channel_attr * Decimal('100')), 2)
            if total_channel_attr > 0
            else 0.0
        )
        channel_rows.append(
            {
                'channel_id': ch.id,
                'name': ch.name,
                'channel_type': ch.channel_type,
                'status': ch.status,
                'campaigns_count': len(ch_campaigns),
                **unit,
                'leads': ch_leads,
                'converted_leads': ch_conv_leads,
                'conversions': len(ch_conv_orders[ch.id]),
                'touchpoints': ch_touches,
                'revenue_share_percent': share,
            }
        )

    campaign_rows.sort(
        key=lambda r: (r['roi'] is not None, r['roi'] or 0.0, r['attributed_revenue']),
        reverse=True,
    )
    channel_rows.sort(
        key=lambda r: (r['attributed_revenue'], r['roi'] or 0.0),
        reverse=True,
    )
    return campaign_rows, channel_rows


def build_summary_kpis(ctx: dict, campaign_rows: list[dict]) -> dict:
    """Compute platform/scoped executive KPIs separating revenue, spend, pipeline, and conversion value."""
    total_spend = quantize_money(sum((c.amount for c in ctx['matched_costs']), ZERO_MONEY))
    attributed_revenue = quantize_money(
        sum((Decimal(str(cr['attributed_revenue'])) for cr in ctx['order_credits']), ZERO_MONEY)
    )
    actual_closed_revenue = quantize_money(
        sum((o.revenue for o in ctx['valid_paid_orders']), ZERO_MONEY)
    )
    duplicate_revenue_excluded = quantize_money(
        sum((o.revenue for o in ctx['duplicate_orders']), ZERO_MONEY)
    )
    open_pipeline_value = quantize_money(
        sum(
            (o.expected_revenue for o in ctx['opportunities'] if o.status == Opportunity.Status.OPEN),
            ZERO_MONEY,
        )
    )
    won_pipeline_value = quantize_money(
        sum(
            (o.actual_revenue for o in ctx['opportunities'] if o.status == Opportunity.Status.WON),
            ZERO_MONEY,
        )
    )

    total_leads = len(ctx['leads'])
    converted_leads = sum(1 for lead in ctx['leads'] if lead.status == Lead.Status.CONVERTED)
    valid_orders_count = len(ctx['valid_paid_orders'])
    total_opportunities = len(ctx['opportunities'])
    won_opportunities = sum(1 for o in ctx['opportunities'] if o.status == Opportunity.Status.WON)

    unit = build_unit_economics(
        attributed_revenue=attributed_revenue,
        marketing_spend=total_spend,
        total_leads=total_leads,
        converted_leads=converted_leads,
    )
    mismatch_by_curr: dict[str, Decimal] = {}
    for c in ctx['mismatched_costs']:
        mismatch_by_curr[c.currency] = quantize_money(
            mismatch_by_curr.get(c.currency, ZERO_MONEY) + c.amount
        )

    return {
        'model_id': ctx['model_id'],
        'model_name': ctx['model_name'],
        'period_label': ctx['period_label'],
        'marketing_spend': unit['marketing_spend'],
        'attributed_revenue': unit['attributed_revenue'],
        'actual_closed_revenue': actual_closed_revenue,
        'pipeline_value': open_pipeline_value,
        'won_pipeline_value': won_pipeline_value,
        'conversion_value': unit['attributed_revenue'],
        'duplicate_revenue_excluded': duplicate_revenue_excluded,
        'roi': unit['roi'],
        'roas': unit['roas'],
        'cpl': unit['cpl'],
        'conversion_rate': unit['conversion_rate'],
        'aov': calculate_aov(actual_closed_revenue, valid_orders_count),
        'valid_orders_count': valid_orders_count,
        'excluded_duplicate_orders': len(ctx['duplicate_orders']),
        'total_campaigns': len(ctx['scoped_campaigns']),
        'total_contacts': Contact.objects.count(),
        'total_touchpoints': sum(1 for tp in ctx['touchpoints'] if tp.is_valid),
        'total_leads': total_leads,
        'converted_leads': converted_leads,
        'total_opportunities': total_opportunities,
        'won_opportunities': won_opportunities,
        'currency_mismatches_count': len(ctx['mismatched_costs']),
        'mismatched_spend_by_currency': mismatch_by_curr,
        'missing_cost_campaigns_count': sum(1 for c in campaign_rows if c['missing_cost_alert']),
    }


def build_creative_performance(ctx: dict) -> list[dict]:
    """Aggregate touchpoint volume, unique contacts, conversions, and attributed revenue per Creative."""
    creatives = list(
        Creative.objects.select_related('primary_campaign')
        .prefetch_related('creative_campaigns')
        .order_by('id')
    )
    scoped_campaign_ids = {c.id for c in ctx['scoped_campaigns']}

    if ctx['is_scoped']:
        creatives = [
            cr
            for cr in creatives
            if cr.primary_campaign_id in scoped_campaign_ids
            or any(link.campaign_id in scoped_campaign_ids for link in cr.creative_campaigns.all())
        ]

    tp_creative_map: dict[str, str] = {}
    cr_touches: dict[str, int] = {cr.id: 0 for cr in creatives}
    cr_contacts: dict[str, set[str]] = {cr.id: set() for cr in creatives}
    cr_attr_rev: dict[str, Decimal] = {cr.id: ZERO_MONEY for cr in creatives}
    cr_orders: dict[str, set[str]] = {cr.id: set() for cr in creatives}

    for tp in ctx['touchpoints']:
        if tp.creative_id:
            tp_creative_map[tp.id] = tp.creative_id
            if tp.is_valid and tp.creative_id in cr_touches:
                cr_touches[tp.creative_id] += 1
                cr_contacts[tp.creative_id].add(tp.contact_id)

    missing_tp_ids = [
        cr['touchpoint_id']
        for cr in ctx['order_credits']
        if cr['touchpoint_id'] not in tp_creative_map
    ]
    if missing_tp_ids:
        for tp_id, creative_id in Touchpoint.objects.filter(
            id__in=missing_tp_ids, creative_id__isnull=False
        ).values_list('id', 'creative_id'):
            tp_creative_map[tp_id] = creative_id

    for credit in ctx['order_credits']:
        cr_id = tp_creative_map.get(credit['touchpoint_id'])
        if cr_id and cr_id in cr_attr_rev:
            cr_attr_rev[cr_id] += Decimal(str(credit['attributed_revenue']))
            if Decimal(str(credit['credit_weight'])) > 0:
                cr_orders[cr_id].add(credit['order_id'])

    total_cr_rev = sum(cr_attr_rev.values(), ZERO_MONEY)
    rows: list[dict] = []
    for cr in creatives:
        linked_campaigns = {link.campaign_id for link in cr.creative_campaigns.all()}
        if cr.primary_campaign_id:
            linked_campaigns.add(cr.primary_campaign_id)
        rev = quantize_money(cr_attr_rev[cr.id])
        share = (
            round(float(rev / total_cr_rev * Decimal('100')), 2)
            if total_cr_rev > 0
            else 0.0
        )
        rows.append(
            {
                'creative_id': cr.id,
                'name': cr.name,
                'creative_type': cr.creative_type,
                'status': cr.status,
                'primary_campaign_id': cr.primary_campaign_id,
                'primary_campaign_name': cr.primary_campaign.name if cr.primary_campaign else None,
                'campaigns_count': len(linked_campaigns),
                'touchpoints': cr_touches[cr.id],
                'unique_contacts': len(cr_contacts[cr.id]),
                'attributed_revenue': rev,
                'conversions': len(cr_orders[cr.id]),
                'revenue_share_percent': share,
            }
        )

    rows.sort(key=lambda r: (r['attributed_revenue'], r['touchpoints']), reverse=True)
    return rows


def build_audience_performance(ctx: dict, campaign_rows: list[dict]) -> list[dict]:
    """Roll up attributed revenue, spend, leads, and ROI across linked CampaignAudiences per segment."""
    campaign_metrics_by_id = {row['campaign_id']: row for row in campaign_rows}
    audiences = list(
        Audience.objects.prefetch_related('audience_campaigns').order_by('id')
    )
    scoped_campaign_ids = {c.id for c in ctx['scoped_campaigns']}

    rows: list[dict] = []
    for aud in audiences:
        linked_ids = [
            link.campaign_id
            for link in aud.audience_campaigns.all()
            if not ctx['is_scoped'] or link.campaign_id in scoped_campaign_ids
        ]
        if ctx['is_scoped'] and not linked_ids:
            continue

        matched_rows = [
            campaign_metrics_by_id[cid] for cid in linked_ids if cid in campaign_metrics_by_id
        ]
        spend = sum((r['marketing_spend'] for r in matched_rows), ZERO_MONEY)
        attr_rev = sum((r['attributed_revenue'] for r in matched_rows), ZERO_MONEY)
        leads_cnt = sum(r['leads'] for r in matched_rows)
        conv_leads = sum(r['converted_leads'] for r in matched_rows)
        conversions = sum(r['conversions'] for r in matched_rows)
        touches = sum(r['touchpoints'] for r in matched_rows)
        unit = build_unit_economics(
            attributed_revenue=attr_rev,
            marketing_spend=spend,
            total_leads=leads_cnt,
            converted_leads=conv_leads,
        )
        rows.append(
            {
                'audience_id': aud.id,
                'name': aud.name,
                'audience_type': aud.audience_type,
                'status': aud.status,
                'estimated_size': aud.estimated_size,
                'campaigns_count': len(matched_rows),
                **unit,
                'leads': leads_cnt,
                'converted_leads': conv_leads,
                'conversions': conversions,
                'touchpoints': touches,
            }
        )

    rows.sort(key=lambda r: (r['attributed_revenue'], r['leads']), reverse=True)
    return rows


def build_roi_analytics(**filters) -> dict:
    """Build complete ROI intelligence payload covering overall, campaign, channel, creative & audience views."""
    ctx = build_analytics_context(**filters)
    campaign_rows, channel_rows = aggregate_campaigns_and_channels(ctx)
    summary = build_summary_kpis(ctx, campaign_rows)

    ranked_with_spend = [row for row in campaign_rows if row['roi'] is not None]
    best_campaigns = ranked_with_spend[:5]
    lowest_campaigns = list(reversed(ranked_with_spend))[:5]
    cost_vs_revenue = [
        {
            'campaign_id': row['campaign_id'],
            'name': row['name'],
            'channel_name': row['channel_name'],
            'spend': row['marketing_spend'],
            'attributed_revenue': row['attributed_revenue'],
            'net_return': quantize_money(row['attributed_revenue'] - row['marketing_spend']),
            'roi': row['roi'],
        }
        for row in campaign_rows
    ]

    return {
        'summary': summary,
        'campaign_rows': campaign_rows,
        'channel_rows': channel_rows,
        'best_campaigns': best_campaigns,
        'lowest_campaigns': lowest_campaigns,
        'cost_vs_revenue': cost_vs_revenue,
    }
