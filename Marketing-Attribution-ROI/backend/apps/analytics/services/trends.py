"""
Monthly Spend/Revenue/ROI time-series analytics (powered by Pandas & NumPy)
and Lead/Opportunity funnel conversion analytics.
"""

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

from apps.analytics.services.metrics import (
    ZERO_MONEY,
    calculate_conversion_rate,
    calculate_roas,
    calculate_roi,
    quantize_money,
)
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity


def _expand_continuous_months(month_keys: set[str]) -> list[str]:
    """Return an ordered, continuous list of `YYYY-MM` keys between observed bounds."""
    if not month_keys:
        return []
    sorted_keys = sorted(month_keys)
    start_year, start_month = map(int, sorted_keys[0].split('-'))
    end_year, end_month = map(int, sorted_keys[-1].split('-'))

    total_months = (end_year - start_year) * 12 + (end_month - start_month) + 1
    if total_months > 36:
        # Guard against huge sparse ranges while still showing all observed active months
        return sorted_keys

    result: list[str] = []
    cur_year, cur_month = start_year, start_month
    for _ in range(total_months):
        result.append(f'{cur_year:04d}-{cur_month:02d}')
        cur_month += 1
        if cur_month > 12:
            cur_month = 1
            cur_year += 1
    return result


def build_monthly_trends(ctx: dict) -> dict:
    """
    Use Pandas & NumPy to construct monthly Marketing Spend, Actual Closed Revenue,
    Attributed Revenue, Orders, Leads, ROI, ROAS, cumulative totals, and descriptive stats.
    """
    cost_records = [
        {'month_key': c.spend_date.strftime('%Y-%m'), 'spend': float(c.amount)}
        for c in ctx['matched_costs']
    ]
    order_records = [
        {'month_key': o.order_date.strftime('%Y-%m'), 'closed_revenue': float(o.revenue)}
        for o in ctx['valid_paid_orders']
    ]
    credit_records = [
        {
            'month_key': cr['order_date'].strftime('%Y-%m'),
            'attributed_revenue': float(cr['attributed_revenue']),
        }
        for cr in ctx['order_credits']
    ]
    lead_records = [
        {'month_key': lead.created_date.strftime('%Y-%m'), 'leads_count': 1}
        for lead in ctx['leads']
    ]

    all_keys: set[str] = set()
    for rows in (cost_records, order_records, credit_records, lead_records):
        for r in rows:
            all_keys.add(r['month_key'])

    ordered_months = _expand_continuous_months(all_keys)
    if not ordered_months:
        return {
            'monthly_series': [],
            'statistics': {
                'total_months': 0,
                'avg_monthly_spend': ZERO_MONEY,
                'avg_monthly_closed_revenue': ZERO_MONEY,
                'avg_monthly_attributed_revenue': ZERO_MONEY,
                'spend_std_dev': 0.0,
                'revenue_std_dev': 0.0,
                'revenue_growth_percent': None,
                'best_month': None,
            },
        }

    base_df = pd.DataFrame({'month_key': ordered_months})

    def _agg_sum(records: list[dict], value_col: str) -> pd.DataFrame:
        if not records:
            return pd.DataFrame({'month_key': ordered_months, value_col: [0.0] * len(ordered_months)})
        df = pd.DataFrame(records)
        return df.groupby('month_key', as_index=False)[value_col].sum()

    def _agg_count(records: list[dict], out_col: str) -> pd.DataFrame:
        if not records:
            return pd.DataFrame({'month_key': ordered_months, out_col: [0] * len(ordered_months)})
        df = pd.DataFrame(records)
        return df.groupby('month_key', as_index=False).size().rename(columns={'size': out_col})

    spend_df = _agg_sum(cost_records, 'spend')
    closed_df = _agg_sum(order_records, 'closed_revenue')
    attr_df = _agg_sum(credit_records, 'attributed_revenue')
    orders_cnt_df = _agg_count(order_records, 'orders_count')
    leads_cnt_df = _agg_count(lead_records, 'leads_count')

    merged = (
        base_df.merge(spend_df, on='month_key', how='left')
        .merge(closed_df, on='month_key', how='left')
        .merge(attr_df, on='month_key', how='left')
        .merge(orders_cnt_df, on='month_key', how='left')
        .merge(leads_cnt_df, on='month_key', how='left')
        .fillna(0.0)
    )

    merged['cumulative_spend'] = merged['spend'].cumsum()
    merged['cumulative_closed_revenue'] = merged['closed_revenue'].cumsum()
    merged['cumulative_attributed_revenue'] = merged['attributed_revenue'].cumsum()

    years_present = {m.split('-')[0] for m in ordered_months}
    single_year = len(years_present) == 1

    monthly_series: list[dict] = []
    for row in merged.to_dict(orient='records'):
        year_num, month_num = map(int, row['month_key'].split('-'))
        dt_obj = date(year_num, month_num, 1)
        label = dt_obj.strftime('%b') if single_year else dt_obj.strftime('%b %Y')

        spend_dec = quantize_money(row['spend'])
        closed_dec = quantize_money(row['closed_revenue'])
        attr_dec = quantize_money(row['attributed_revenue'])

        # Revenue basis for monthly ROI uses attributed revenue when credits exist, else closed revenue
        roi_basis = attr_dec if attr_dec > ZERO_MONEY else closed_dec
        monthly_series.append(
            {
                'month_key': row['month_key'],
                'month': label,
                'spend': spend_dec,
                'closed_revenue': closed_dec,
                'attributed_revenue': attr_dec,
                'revenue': closed_dec,
                'orders_count': int(row['orders_count']),
                'leads_count': int(row['leads_count']),
                'roi': calculate_roi(roi_basis, spend_dec),
                'roas': calculate_roas(roi_basis, spend_dec),
                'cumulative_spend': quantize_money(row['cumulative_spend']),
                'cumulative_closed_revenue': quantize_money(row['cumulative_closed_revenue']),
                'cumulative_attributed_revenue': quantize_money(row['cumulative_attributed_revenue']),
            }
        )

    spend_arr = np.asarray(merged['spend'].values, dtype=float)
    closed_arr = np.asarray(merged['closed_revenue'].values, dtype=float)
    attr_arr = np.asarray(merged['attributed_revenue'].values, dtype=float)

    revenue_growth_pct: float | None = None
    non_zero_indices = np.where(closed_arr > 0)[0]
    if len(non_zero_indices) >= 2:
        first_rev = float(closed_arr[non_zero_indices[0]])
        last_rev = float(closed_arr[non_zero_indices[-1]])
        if first_rev > 0:
            revenue_growth_pct = round(((last_rev - first_rev) / first_rev) * 100.0, 2)

    best_idx = int(np.argmax(closed_arr)) if len(closed_arr) > 0 else 0
    best_row = monthly_series[best_idx]

    return {
        'monthly_series': monthly_series,
        'statistics': {
            'total_months': len(monthly_series),
            'avg_monthly_spend': quantize_money(float(np.mean(spend_arr))),
            'avg_monthly_closed_revenue': quantize_money(float(np.mean(closed_arr))),
            'avg_monthly_attributed_revenue': quantize_money(float(np.mean(attr_arr))),
            'spend_std_dev': round(float(np.std(spend_arr)), 2),
            'revenue_std_dev': round(float(np.std(closed_arr)), 2),
            'revenue_growth_percent': revenue_growth_pct,
            'best_month': {
                'month_key': best_row['month_key'],
                'month': best_row['month'],
                'closed_revenue': best_row['closed_revenue'],
                'attributed_revenue': best_row['attributed_revenue'],
            },
        },
    }


def build_funnel_analytics(ctx: dict) -> dict:
    """Compute Lead lifecycle conversion and 6-stage Opportunity pipeline analytics."""
    leads: list[Lead] = ctx['leads']
    opportunities: list[Opportunity] = ctx['opportunities']
    valid_orders = ctx['valid_paid_orders']
    valid_touchpoints_count = sum(1 for tp in ctx['touchpoints'] if tp.is_valid)
    unique_contacts = {tp.contact_id for tp in ctx['touchpoints'] if tp.is_valid}

    lead_status_counts = {choice.value: 0 for choice in Lead.Status}
    for lead in leads:
        if lead.status in lead_status_counts:
            lead_status_counts[lead.status] += 1

    qualified_or_converted = (
        lead_status_counts.get(Lead.Status.MQL, 0)
        + lead_status_counts.get(Lead.Status.SQL, 0)
        + lead_status_counts.get(Lead.Status.CONVERTED, 0)
    )
    won_opps = [o for o in opportunities if o.status == Opportunity.Status.WON]
    open_opps = [o for o in opportunities if o.status == Opportunity.Status.OPEN]
    lost_opps = [o for o in opportunities if o.status == Opportunity.Status.LOST]

    funnel_stages = [
        {'stage': 'Touchpoints', 'count': valid_touchpoints_count},
        {'stage': 'Engaged Contacts', 'count': len(unique_contacts)},
        {'stage': 'Total Leads', 'count': len(leads)},
        {'stage': 'MQL / SQL / Converted', 'count': qualified_or_converted},
        {'stage': 'Opportunities', 'count': len(opportunities)},
        {'stage': 'Closed Won Deals', 'count': len(won_opps)},
        {'stage': 'Verified Paid Orders', 'count': len(valid_orders)},
    ]

    opp_by_stage: dict[str, dict] = {
        st.value: {
            'stage': st.value,
            'count': 0,
            'expected_revenue': ZERO_MONEY,
            'actual_revenue': ZERO_MONEY,
        }
        for st in Opportunity.Stage
    }
    for opp in opportunities:
        if opp.stage in opp_by_stage:
            opp_by_stage[opp.stage]['count'] += 1
            opp_by_stage[opp.stage]['expected_revenue'] += opp.expected_revenue
            opp_by_stage[opp.stage]['actual_revenue'] += opp.actual_revenue

    opportunity_stage_breakdown = [
        {
            'stage': row['stage'],
            'count': row['count'],
            'expected_revenue': quantize_money(row['expected_revenue']),
            'actual_revenue': quantize_money(row['actual_revenue']),
        }
        for row in opp_by_stage.values()
    ]

    open_pipeline_value = quantize_money(sum((o.expected_revenue for o in open_opps), ZERO_MONEY))
    won_revenue = quantize_money(sum((o.actual_revenue for o in won_opps), ZERO_MONEY))
    closed_total = len(won_opps) + len(lost_opps)
    avg_deal_size = (
        quantize_money(won_revenue / Decimal(len(won_opps)))
        if won_opps
        else ZERO_MONEY
    )

    lead_conversion_rate = calculate_conversion_rate(
        lead_status_counts.get(Lead.Status.CONVERTED, 0),
        len(leads),
    )
    opp_win_rate = calculate_conversion_rate(len(won_opps), closed_total or len(opportunities))

    return {
        'model_id': ctx['model_id'],
        'period_label': ctx['period_label'],
        'funnel_stages': funnel_stages,
        'lead_summary': {
            'total_leads': len(leads),
            'converted_leads': lead_status_counts.get(Lead.Status.CONVERTED, 0),
            'lead_conversion_rate': lead_conversion_rate,
            'by_status': [
                {'status': status_name, 'count': cnt}
                for status_name, cnt in lead_status_counts.items()
            ],
        },
        'opportunity_summary': {
            'total_opportunities': len(opportunities),
            'open_opportunities': len(open_opps),
            'won_opportunities': len(won_opps),
            'lost_opportunities': len(lost_opps),
            'open_pipeline_value': open_pipeline_value,
            'won_revenue': won_revenue,
            'win_rate': opp_win_rate,
            'avg_deal_size': avg_deal_size,
            'by_stage': opportunity_stage_breakdown,
        },
    }

