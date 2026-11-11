"""
Core multi-touch attribution calculation engine, persistence layer, and 5-model comparator.

Orchestrates order eligibility validation, conversion-window touchpoint filtering,
pluggable weight calculators, penny-exact revenue reconciliation, and auditable storage.
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun
from apps.attribution.services import (
    first_touch,
    last_touch,
    linear,
    position_based,
    time_decay,
)
from apps.attribution.services.attribution_validator import (
    CURRENCY_QUANTUM,
    ZERO_MONEY,
    allocate_order_revenue,
    filter_eligible_touchpoints,
    order_conversion_cutoff,
    validate_order_eligibility,
    verify_order_reconciliation,
)
from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from common.audit import record_audit_log
from common.sequences import generate_deterministic_id_batch

MODEL_CALCULATORS = {
    AttributionModel.ModelCode.FIRST_TOUCH: first_touch.calculate_weights,
    AttributionModel.ModelCode.LAST_TOUCH: last_touch.calculate_weights,
    AttributionModel.ModelCode.LINEAR: linear.calculate_weights,
    AttributionModel.ModelCode.TIME_DECAY: time_decay.calculate_weights,
    AttributionModel.ModelCode.POSITION_BASED: position_based.calculate_weights,
}

DEFAULT_MODEL_DEFINITIONS = [
    {
        'id': AttributionModel.ModelCode.FIRST_TOUCH,
        'name': 'First Touch',
        'short_label': 'First Touch',
        'description': (
            "Assigns 100% of verified closed order revenue credit to the contact's "
            'earliest eligible marketing touchpoint within the conversion window.'
        ),
        'rule_version': '1.0.0',
        'config': {'first_touch_weight': 1.0},
    },
    {
        'id': AttributionModel.ModelCode.LAST_TOUCH,
        'name': 'Last Touch',
        'short_label': 'Last Touch',
        'description': (
            'Assigns 100% of verified closed order revenue credit to the final '
            'pre-conversion marketing touchpoint before order close.'
        ),
        'rule_version': '1.0.0',
        'config': {'last_touch_weight': 1.0},
    },
    {
        'id': AttributionModel.ModelCode.LINEAR,
        'name': 'Linear',
        'short_label': 'Linear',
        'description': (
            'Distributes closed order revenue equally across every eligible '
            'pre-conversion touchpoint along the buyer journey.'
        ),
        'rule_version': '1.0.0',
        'config': {'equal_split': True},
    },
    {
        'id': AttributionModel.ModelCode.TIME_DECAY,
        'name': 'Time Decay',
        'short_label': 'Time Decay',
        'description': (
            'Applies an exponential half-life decay formula w_i = 2^(-age_days_i / H) '
            'so touchpoints closer to conversion receive higher credit.'
        ),
        'rule_version': '1.0.0',
        'config': {'half_life_days': 7},
    },
    {
        'id': AttributionModel.ModelCode.POSITION_BASED,
        'name': 'Position Based',
        'short_label': 'Position Based',
        'description': (
            'U-shaped allocation assigning 40% to First Touch, 40% to Last Touch, '
            'and splitting 20% evenly across intermediate touches (100% if 1 touch, 50/50 if 2).'
        ),
        'rule_version': '1.0.0',
        'config': {'first_weight': 0.4, 'last_weight': 0.4, 'middle_pool': 0.2},
    },
]


def ensure_attribution_models_seeded() -> list[AttributionModel]:
    """Ensure all 5 canonical attribution models exist in DB without overwriting overrides."""
    models: list[AttributionModel] = []
    for entry in DEFAULT_MODEL_DEFINITIONS:
        obj, _ = AttributionModel.objects.get_or_create(
            id=entry['id'],
            defaults={
                'name': entry['name'],
                'short_label': entry['short_label'],
                'description': entry['description'],
                'rule_version': entry['rule_version'],
                'config': entry['config'],
                'is_active': True,
            },
        )
        models.append(obj)
    return list(AttributionModel.objects.all().order_by('id'))


def resolve_date_bounds(
    *,
    date_range: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[date | None, date | None, str]:
    """Resolve explicit dates or preset date_range strings into `(start_date, end_date, label)`."""
    if date_from or date_to:
        label = f"{date_from.isoformat() if date_from else '...'} to {date_to.isoformat() if date_to else '...'}"
        return date_from, date_to, label

    preset = (date_range or 'all_time').strip().lower()
    if preset == 'ytd_2026':
        return date(2026, 1, 1), date(2026, 12, 31), 'YTD 2026'
    if preset in ('last_30_days', '30d'):
        end = timezone.localdate()
        return end - timedelta(days=30), end, 'Last 30 Days'
    if preset in ('last_90_days', '90d'):
        end = timezone.localdate()
        return end - timedelta(days=90), end, 'Last 90 Days'
    return None, None, 'All Time'


def _load_attribution_dataset(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Load orders, touchpoints, campaigns, and channels in O(1) bulk queries."""
    campaigns = list(Campaign.objects.select_related('channel').order_by('id'))
    channels = list(Channel.objects.all().order_by('id'))

    orders_qs = Order.objects.select_related('contact', 'opportunity').order_by('order_date', 'id')
    if date_from is not None:
        orders_qs = orders_qs.filter(order_date__gte=date_from)
    if date_to is not None:
        orders_qs = orders_qs.filter(order_date__lte=date_to)
    orders = list(orders_qs)

    valid_orders: list[Order] = []
    excluded_duplicate_orders = 0
    excluded_other_orders = 0
    for ord_obj in orders:
        is_ok, reason = validate_order_eligibility(ord_obj)
        if is_ok:
            valid_orders.append(ord_obj)
        elif reason == 'duplicate':
            excluded_duplicate_orders += 1
        else:
            excluded_other_orders += 1

    contact_ids = list({o.contact_id for o in valid_orders})
    touchpoints_by_contact: dict[str, list[Touchpoint]] = {cid: [] for cid in contact_ids}
    if contact_ids:
        all_tps = (
            Touchpoint.objects.filter(contact_id__in=contact_ids)
            .select_related('campaign', 'channel', 'creative', 'session')
            .order_by('timestamp', 'id')
        )
        for tp in all_tps:
            touchpoints_by_contact[tp.contact_id].append(tp)

    return {
        'campaigns': campaigns,
        'channels': channels,
        'valid_orders': valid_orders,
        'excluded_duplicate_orders': excluded_duplicate_orders,
        'excluded_other_orders': excluded_other_orders,
        'touchpoints_by_contact': touchpoints_by_contact,
    }


def _compute_model_allocations(
    *,
    model_obj: AttributionModel,
    dataset: dict,
    conversion_window_days: int,
    half_life_days: int,
) -> dict:
    """Compute attribution weights, revenues, and rollups for a single model against loaded data."""
    calculator = MODEL_CALCULATORS.get(model_obj.id)
    if calculator is None:
        raise ValidationError({'model_id': [f'Unsupported attribution model "{model_obj.id}".']})

    campaigns: list[Campaign] = dataset['campaigns']
    channels: list[Channel] = dataset['channels']
    valid_orders: list[Order] = dataset['valid_orders']
    touchpoints_by_contact: dict[str, list[Touchpoint]] = dataset['touchpoints_by_contact']

    campaign_map = {c.id: c for c in campaigns}
    channel_map = {ch.id: ch for ch in channels}

    by_campaign: dict[str, dict] = {
        c.id: {
            'campaign_id': c.id,
            'campaign_name': c.name,
            'channel_id': c.channel_id,
            'channel_name': channel_map[c.channel_id].name if c.channel_id in channel_map else 'Unknown',
            'attributed_revenue': ZERO_MONEY,
            'conversions': 0,
            'touch_credit_count': Decimal('0.000000'),
        }
        for c in campaigns
    }
    by_channel: dict[str, dict] = {
        ch.id: {
            'channel_id': ch.id,
            'channel_name': ch.name,
            'channel_type': ch.channel_type,
            'attributed_revenue': ZERO_MONEY,
            'conversions': 0,
        }
        for ch in channels
    }

    order_credits: list[dict] = []
    excluded_post_conversion = 0
    excluded_outside_window = 0
    excluded_unverified_sessions = 0
    excluded_invalid_touches = 0

    valid_orders_with_touches = 0
    orders_without_eligible_touches = 0
    total_closed_valid_revenue = ZERO_MONEY
    total_attributed_revenue = ZERO_MONEY
    unattributed_valid_revenue = ZERO_MONEY

    for order in valid_orders:
        order_rev = Decimal(order.revenue).quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
        total_closed_valid_revenue += order_rev
        cutoff = order_conversion_cutoff(order)
        contact_touches = touchpoints_by_contact.get(order.contact_id, [])

        eligible, ex_stats = filter_eligible_touchpoints(
            contact_touches,
            conversion_cutoff=cutoff,
            conversion_window_days=conversion_window_days,
        )
        excluded_post_conversion += ex_stats['excluded_post_conversion']
        excluded_outside_window += ex_stats['excluded_outside_window']
        excluded_unverified_sessions += ex_stats['excluded_unverified_session']
        excluded_invalid_touches += ex_stats['excluded_invalid']

        if not eligible:
            orders_without_eligible_touches += 1
            unattributed_valid_revenue += order_rev
            continue

        valid_orders_with_touches += 1
        weights = calculator(
            eligible,
            conversion_cutoff=cutoff,
            half_life_days=half_life_days,
        )
        revenues = allocate_order_revenue(order_rev, weights)
        verify_order_reconciliation(
            order_id=order.id,
            order_revenue=order_rev,
            weights=weights,
            revenues=revenues,
        )

        credited_campaigns_for_order: set[str] = set()
        credited_channels_for_order: set[str] = set()

        for tp, weight, credit in zip(eligible, weights, revenues):
            total_attributed_revenue += credit
            cmp_key = tp.campaign_id or 'UNATTRIBUTED'
            ch_key = (
                tp.channel_id
                or (campaign_map[tp.campaign_id].channel_id if tp.campaign_id in campaign_map else None)
                or 'UNATTRIBUTED'
            )

            if cmp_key not in by_campaign:
                by_campaign[cmp_key] = {
                    'campaign_id': None if cmp_key == 'UNATTRIBUTED' else cmp_key,
                    'campaign_name': 'Unassigned Campaign' if cmp_key == 'UNATTRIBUTED' else cmp_key,
                    'channel_id': None if ch_key == 'UNATTRIBUTED' else ch_key,
                    'channel_name': channel_map[ch_key].name if ch_key in channel_map else 'Unassigned Channel',
                    'attributed_revenue': ZERO_MONEY,
                    'conversions': 0,
                    'touch_credit_count': Decimal('0.000000'),
                }

            by_campaign[cmp_key]['attributed_revenue'] += credit
            by_campaign[cmp_key]['touch_credit_count'] += weight
            if weight > 0 and cmp_key not in credited_campaigns_for_order:
                by_campaign[cmp_key]['conversions'] += 1
                credited_campaigns_for_order.add(cmp_key)

            if ch_key not in by_channel:
                by_channel[ch_key] = {
                    'channel_id': None if ch_key == 'UNATTRIBUTED' else ch_key,
                    'channel_name': 'Unassigned Channel' if ch_key == 'UNATTRIBUTED' else ch_key,
                    'channel_type': 'Unattributed',
                    'attributed_revenue': ZERO_MONEY,
                    'conversions': 0,
                }
            by_channel[ch_key]['attributed_revenue'] += credit
            if weight > 0 and ch_key not in credited_channels_for_order:
                by_channel[ch_key]['conversions'] += 1
                credited_channels_for_order.add(ch_key)

            order_credits.append(
                {
                    'order_id': order.id,
                    'contact_id': order.contact_id,
                    'order_date': order.order_date,
                    'order_revenue': order_rev,
                    'currency': order.currency,
                    'touchpoint_id': tp.id,
                    'campaign_id': tp.campaign_id,
                    'campaign_name': (
                        campaign_map[tp.campaign_id].name
                        if tp.campaign_id in campaign_map
                        else 'Unassigned Campaign'
                    ),
                    'channel_id': None if ch_key == 'UNATTRIBUTED' else ch_key,
                    'channel_name': (
                        channel_map[ch_key].name
                        if ch_key in channel_map
                        else 'Unassigned Channel'
                    ),
                    'timestamp': tp.timestamp,
                    'is_online': tp.is_online,
                    'credit_weight': weight,
                    'weight_percent': round(float(weight) * 100.0, 2),
                    'attributed_revenue': credit,
                }
            )

    campaign_results = []
    for row in by_campaign.values():
        rev = row['attributed_revenue'].quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
        share = (
            round(float(rev / total_attributed_revenue * Decimal('100')), 2)
            if total_attributed_revenue > 0
            else 0.0
        )
        campaign_results.append(
            {
                'campaign_id': row['campaign_id'],
                'campaign_name': row['campaign_name'],
                'channel_id': row['channel_id'],
                'channel_name': row['channel_name'],
                'attributed_revenue': rev,
                'conversions': row['conversions'],
                'touch_credit_count': round(float(row['touch_credit_count']), 4),
                'share_percent': share,
            }
        )

    channel_results = []
    for row in by_channel.values():
        rev = row['attributed_revenue'].quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
        share = (
            round(float(rev / total_attributed_revenue * Decimal('100')), 2)
            if total_attributed_revenue > 0
            else 0.0
        )
        channel_results.append(
            {
                'channel_id': row['channel_id'],
                'channel_name': row['channel_name'],
                'channel_type': row['channel_type'],
                'attributed_revenue': rev,
                'conversions': row['conversions'],
                'share_percent': share,
            }
        )

    return {
        'model_id': model_obj.id,
        'model_name': model_obj.name,
        'rule_version': model_obj.rule_version,
        'conversion_window_days': conversion_window_days,
        'half_life_days': half_life_days,
        'valid_orders_processed': valid_orders_with_touches,
        'orders_without_eligible_touches': orders_without_eligible_touches,
        'excluded_duplicate_orders': dataset['excluded_duplicate_orders'],
        'excluded_other_orders': dataset['excluded_other_orders'],
        'excluded_post_conversion_touches': excluded_post_conversion,
        'excluded_outside_window_touches': excluded_outside_window,
        'excluded_unverified_session_touches': excluded_unverified_sessions,
        'excluded_invalid_touches': excluded_invalid_touches,
        'total_closed_valid_revenue': total_closed_valid_revenue.quantize(CURRENCY_QUANTUM),
        'total_attributed_revenue': total_attributed_revenue.quantize(CURRENCY_QUANTUM),
        'unattributed_valid_revenue': unattributed_valid_revenue.quantize(CURRENCY_QUANTUM),
        'campaign_results': campaign_results,
        'channel_results': channel_results,
        'order_credits': order_credits,
    }


def _persist_run_and_results(
    *,
    model_obj: AttributionModel,
    period_label: str,
    computed: dict,
    actor=None,
    source_ip: str | None = None,
) -> AttributionRun:
    """Atomically store an AttributionRun and batch-insert all AttributionResult rows."""
    resolved_actor = actor if (actor and getattr(actor, 'is_authenticated', False)) else None
    run = AttributionRun.objects.create(
        attribution_model=model_obj,
        rule_version=model_obj.rule_version,
        period_label=period_label,
        conversion_window_days=computed['conversion_window_days'],
        half_life_days=computed['half_life_days'],
        valid_orders_processed=computed['valid_orders_processed'],
        excluded_duplicate_orders=computed['excluded_duplicate_orders'],
        excluded_post_conversion_touches=computed['excluded_post_conversion_touches'],
        total_attributed_revenue=computed['total_attributed_revenue'],
        status=AttributionRun.Status.COMPLETED,
        executed_by=resolved_actor,
    )

    credits = computed['order_credits']
    if credits:
        batch_ids = generate_deterministic_id_batch(
            prefix='ATTR-RES',
            model_cls=AttributionResult,
            count=len(credits),
        )
        rows = [
            AttributionResult(
                id=res_id,
                run=run,
                attribution_model=model_obj,
                order_id=item['order_id'],
                touchpoint_id=item['touchpoint_id'],
                campaign_id=item['campaign_id'],
                channel_id=item['channel_id'],
                contact_id=item['contact_id'],
                rule_version=model_obj.rule_version,
                credit_weight=item['credit_weight'],
                attributed_revenue=item['attributed_revenue'],
                source_order_revenue=item['order_revenue'],
                currency=item['currency'],
            )
            for res_id, item in zip(batch_ids, credits)
        ]
        AttributionResult.objects.bulk_create(rows)

    record_audit_log(
        entity_type='AttributionRun',
        entity_id=run.id,
        action=AuditLog.Action.CREATE,
        actor=resolved_actor,
        previous_state=None,
        new_state={
            'run_id': run.id,
            'model_id': model_obj.id,
            'rule_version': model_obj.rule_version,
            'conversion_window_days': run.conversion_window_days,
            'half_life_days': run.half_life_days,
            'valid_orders_processed': run.valid_orders_processed,
            'excluded_duplicate_orders': run.excluded_duplicate_orders,
            'excluded_post_conversion_touches': run.excluded_post_conversion_touches,
            'total_attributed_revenue': str(run.total_attributed_revenue),
            'result_rows_created': len(credits),
        },
        changed_fields=['status', 'total_attributed_revenue', 'results'],
        source_ip=source_ip,
        notes=f'Executed {model_obj.name} attribution run ({period_label}).',
    )
    return run


@transaction.atomic
def execute_attribution_run(
    *,
    model_id: str | None = None,
    conversion_window_days: int | None = None,
    half_life_days: int | None = None,
    period_label: str | None = None,
    date_range: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    persist: bool = True,
    actor=None,
    source_ip: str | None = None,
) -> dict:
    """Execute attribution calculation for one model and optionally persist run/results."""
    ensure_attribution_models_seeded()

    target_model = model_id or settings.ATTRIBUTION_SETTINGS.get('DEFAULT_MODEL', 'position_based')
    model_obj = AttributionModel.objects.filter(id=target_model).first()
    if model_obj is None:
        raise ValidationError({'model_id': [f'Unknown attribution model "{target_model}".']})
    if not model_obj.is_active:
        raise ValidationError({'model_id': [f'Attribution model "{target_model}" is inactive.']})

    effective_window = int(
        conversion_window_days
        if conversion_window_days is not None
        else settings.ATTRIBUTION_SETTINGS.get('CONVERSION_WINDOW_DAYS', 90)
    )
    effective_half_life = int(
        half_life_days
        if half_life_days is not None
        else model_obj.config.get(
            'half_life_days',
            settings.ATTRIBUTION_SETTINGS.get('TIME_DECAY_HALF_LIFE_DAYS', 7),
        )
    )
    if effective_window < 1:
        raise ValidationError({'conversion_window_days': ['Must be at least 1 day.']})
    if effective_half_life < 1:
        raise ValidationError({'half_life_days': ['Must be at least 1 day.']})

    bound_start, bound_end, resolved_label = resolve_date_bounds(
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )
    final_label = (period_label or '').strip() or resolved_label

    dataset = _load_attribution_dataset(date_from=bound_start, date_to=bound_end)
    computed = _compute_model_allocations(
        model_obj=model_obj,
        dataset=dataset,
        conversion_window_days=effective_window,
        half_life_days=effective_half_life,
    )

    run_obj = None
    if persist:
        run_obj = _persist_run_and_results(
            model_obj=model_obj,
            period_label=final_label,
            computed=computed,
            actor=actor,
            source_ip=source_ip,
        )

    computed['run_id'] = run_obj.id if run_obj else None
    computed['executed_at'] = run_obj.executed_at if run_obj else timezone.now()
    computed['period_label'] = final_label
    computed['persisted'] = persist
    return computed


def compare_attribution_models(
    *,
    conversion_window_days: int | None = None,
    half_life_days: int | None = None,
    date_range: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    Evaluate all 5 attribution models side-by-side against the exact same order/touchpoint
    dataset snapshot and return Recharts-compatible campaign and channel comparison matrices.
    """
    all_models = ensure_attribution_models_seeded()
    effective_window = int(
        conversion_window_days
        if conversion_window_days is not None
        else settings.ATTRIBUTION_SETTINGS.get('CONVERSION_WINDOW_DAYS', 90)
    )
    effective_half_life = int(
        half_life_days
        if half_life_days is not None
        else settings.ATTRIBUTION_SETTINGS.get('TIME_DECAY_HALF_LIFE_DAYS', 7)
    )
    if effective_window < 1:
        raise ValidationError({'conversion_window_days': ['Must be at least 1 day.']})
    if effective_half_life < 1:
        raise ValidationError({'half_life_days': ['Must be at least 1 day.']})

    bound_start, bound_end, resolved_label = resolve_date_bounds(
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )
    dataset = _load_attribution_dataset(date_from=bound_start, date_to=bound_end)

    model_ids = [
        AttributionModel.ModelCode.FIRST_TOUCH,
        AttributionModel.ModelCode.LAST_TOUCH,
        AttributionModel.ModelCode.LINEAR,
        AttributionModel.ModelCode.TIME_DECAY,
        AttributionModel.ModelCode.POSITION_BASED,
    ]
    models_by_id = {m.id: m for m in all_models}

    runs_summary: dict[str, dict] = {}
    campaign_index: dict[str, dict] = {}
    channel_index: dict[str, dict] = {}

    for m_id in model_ids:
        model_obj = models_by_id[m_id]
        computed = _compute_model_allocations(
            model_obj=model_obj,
            dataset=dataset,
            conversion_window_days=effective_window,
            half_life_days=effective_half_life,
        )
        runs_summary[m_id] = {
            'model_id': computed['model_id'],
            'model_name': computed['model_name'],
            'valid_orders_processed': computed['valid_orders_processed'],
            'total_attributed_revenue': computed['total_attributed_revenue'],
            'campaign_results': computed['campaign_results'],
            'channel_results': computed['channel_results'],
        }

        for crow in computed['campaign_results']:
            key = crow['campaign_id'] or 'UNATTRIBUTED'
            if key not in campaign_index:
                campaign_index[key] = {
                    'campaign_id': crow['campaign_id'],
                    'campaign_name': crow['campaign_name'],
                    'channel_name': crow['channel_name'],
                    'first_touch': ZERO_MONEY,
                    'last_touch': ZERO_MONEY,
                    'linear': ZERO_MONEY,
                    'time_decay': ZERO_MONEY,
                    'position_based': ZERO_MONEY,
                }
            campaign_index[key][m_id] = crow['attributed_revenue']

        for chrow in computed['channel_results']:
            key = chrow['channel_id'] or 'UNATTRIBUTED'
            if key not in channel_index:
                channel_index[key] = {
                    'channel_id': chrow['channel_id'],
                    'channel_name': chrow['channel_name'],
                    'channel_type': chrow['channel_type'],
                    'first_touch': ZERO_MONEY,
                    'last_touch': ZERO_MONEY,
                    'linear': ZERO_MONEY,
                    'time_decay': ZERO_MONEY,
                    'position_based': ZERO_MONEY,
                }
            channel_index[key][m_id] = chrow['attributed_revenue']

    return {
        'period_label': resolved_label,
        'conversion_window_days': effective_window,
        'half_life_days': effective_half_life,
        'valid_orders_count': len(dataset['valid_orders']),
        'excluded_duplicate_orders': dataset['excluded_duplicate_orders'],
        'runs': runs_summary,
        'campaign_comparison': list(campaign_index.values()),
        'channel_comparison': list(channel_index.values()),
    }


def serialize_run_payload(run: AttributionRun) -> dict:
    """Reconstruct persisted campaign and channel breakdowns for a saved AttributionRun."""
    rows = list(
        AttributionResult.objects.filter(run=run)
        .select_related('campaign', 'channel', 'order', 'touchpoint')
        .order_by('order_id', 'touchpoint__timestamp', 'id')
    )
    total_rev = run.total_attributed_revenue

    by_campaign: dict[str, dict] = {}
    by_channel: dict[str, dict] = {}
    seen_cmp_orders: dict[str, set[str]] = {}
    seen_ch_orders: dict[str, set[str]] = {}

    for res in rows:
        cmp_key = res.campaign_id or 'UNATTRIBUTED'
        ch_key = res.channel_id or 'UNATTRIBUTED'

        if cmp_key not in by_campaign:
            by_campaign[cmp_key] = {
                'campaign_id': res.campaign_id,
                'campaign_name': res.campaign.name if res.campaign else 'Unassigned Campaign',
                'channel_id': res.channel_id,
                'channel_name': res.channel.name if res.channel else 'Unassigned Channel',
                'attributed_revenue': ZERO_MONEY,
                'conversions': 0,
                'touch_credit_count': Decimal('0.000000'),
                'share_percent': 0.0,
            }
            seen_cmp_orders[cmp_key] = set()
        by_campaign[cmp_key]['attributed_revenue'] += res.attributed_revenue
        by_campaign[cmp_key]['touch_credit_count'] += res.credit_weight
        if res.credit_weight > 0 and res.order_id not in seen_cmp_orders[cmp_key]:
            by_campaign[cmp_key]['conversions'] += 1
            seen_cmp_orders[cmp_key].add(res.order_id)

        if ch_key not in by_channel:
            by_channel[ch_key] = {
                'channel_id': res.channel_id,
                'channel_name': res.channel.name if res.channel else 'Unassigned Channel',
                'channel_type': res.channel.channel_type if res.channel else 'Unattributed',
                'attributed_revenue': ZERO_MONEY,
                'conversions': 0,
                'share_percent': 0.0,
            }
            seen_ch_orders[ch_key] = set()
        by_channel[ch_key]['attributed_revenue'] += res.attributed_revenue
        if res.credit_weight > 0 and res.order_id not in seen_ch_orders[ch_key]:
            by_channel[ch_key]['conversions'] += 1
            seen_ch_orders[ch_key].add(res.order_id)

    campaign_breakdown = []
    for entry in by_campaign.values():
        rev = entry['attributed_revenue'].quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
        share = round(float(rev / total_rev * Decimal('100')), 2) if total_rev > 0 else 0.0
        campaign_breakdown.append(
            {
                **entry,
                'attributed_revenue': rev,
                'touch_credit_count': round(float(entry['touch_credit_count']), 4),
                'share_percent': share,
            }
        )

    channel_breakdown = []
    for entry in by_channel.values():
        rev = entry['attributed_revenue'].quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
        share = round(float(rev / total_rev * Decimal('100')), 2) if total_rev > 0 else 0.0
        channel_breakdown.append({**entry, 'attributed_revenue': rev, 'share_percent': share})

    return {
        'run': run,
        'campaign_breakdown': sorted(
            campaign_breakdown,
            key=lambda x: (-x['attributed_revenue'], x['campaign_name']),
        ),
        'channel_breakdown': sorted(
            channel_breakdown,
            key=lambda x: (-x['attributed_revenue'], x['channel_name']),
        ),
        'result_count': len(rows),
        'results': rows,
    }


def update_attribution_model(
    *,
    model_obj: AttributionModel,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> AttributionModel:
    """Update AttributionModel configuration/version/status and log AuditLog."""
    previous_state = {
        'id': model_obj.id,
        'name': model_obj.name,
        'rule_version': model_obj.rule_version,
        'config': model_obj.config,
        'is_active': model_obj.is_active,
    }
    changed_fields = []
    for field, val in validated_data.items():
        if getattr(model_obj, field) != val:
            setattr(model_obj, field, val)
            changed_fields.append(field)

    if changed_fields:
        model_obj.save()
        record_audit_log(
            entity_type='AttributionModel',
            entity_id=model_obj.id,
            action=AuditLog.Action.UPDATE,
            actor=actor,
            previous_state=previous_state,
            new_state={
                'id': model_obj.id,
                'name': model_obj.name,
                'rule_version': model_obj.rule_version,
                'config': model_obj.config,
                'is_active': model_obj.is_active,
            },
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes=f'Updated attribution model {model_obj.id}.',
        )
    return model_obj
