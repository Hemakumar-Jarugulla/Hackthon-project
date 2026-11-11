"""
Automated anomaly detection service for the 5 core Marketing Attribution & ROI data quality issues.

Never silently mutates source records; records structured DataException alerts for auditability.
"""

from datetime import datetime, timezone as dt_timezone

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.attribution.models import AttributionResult
from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign
from apps.costs.models import CostRecord
from apps.exceptions.models import DataException
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.web_sessions.models import WebSession
from common.audit import record_audit_log
from common.sequences import generate_deterministic_id_batch


def _detect_duplicate_revenue_candidates() -> list[dict]:
    """Problem 1: Revenue counted more than once (explicit Duplicate status or multi-valid per opp)."""
    candidates: list[dict] = []
    seen_order_ids: set[str] = set()

    dup_orders = Order.objects.filter(
        verification_status=Order.VerificationStatus.DUPLICATE
    ).select_related('opportunity', 'contact')
    for ord_obj in dup_orders:
        seen_order_ids.add(ord_obj.id)
        candidates.append(
            {
                'issue_type': DataException.IssueType.DUPLICATE_REVENUE,
                'entity_type': DataException.EntityType.ORDER,
                'entity_id': ord_obj.id,
                'severity': DataException.Severity.CRITICAL,
                'description': (
                    f'Order {ord_obj.id} (${ord_obj.revenue} {ord_obj.currency}) is flagged as Duplicate '
                    f'on opportunity {ord_obj.opportunity_id} for contact {ord_obj.contact_id}.'
                ),
                'expected_decision': (
                    f'Exclude duplicate order {ord_obj.id} from verified closed revenue '
                    'and multi-touch attribution calculations.'
                ),
                'actual_decision': (
                    'Quarantined with verification_status=Duplicate; excluded from verified totals.'
                ),
                'created_date': ord_obj.order_date,
            }
        )

    multi_valid_opps = (
        Order.objects.filter(
            verification_status=Order.VerificationStatus.VALID,
            payment_status=Order.PaymentStatus.PAID,
        )
        .order_by()
        .values('opportunity_id')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
    )
    multi_opp_ids = [row['opportunity_id'] for row in multi_valid_opps]
    if multi_opp_ids:
        extra_orders = Order.objects.filter(
            opportunity_id__in=multi_opp_ids,
            verification_status=Order.VerificationStatus.VALID,
            payment_status=Order.PaymentStatus.PAID,
        ).order_by('opportunity_id', 'order_date', 'id')
        seen_opps: set[str] = set()
        for ord_obj in extra_orders:
            if ord_obj.opportunity_id not in seen_opps:
                seen_opps.add(ord_obj.opportunity_id)
                continue
            if ord_obj.id in seen_order_ids:
                continue
            candidates.append(
                {
                    'issue_type': DataException.IssueType.DUPLICATE_REVENUE,
                    'entity_type': DataException.EntityType.ORDER,
                    'entity_id': ord_obj.id,
                    'severity': DataException.Severity.CRITICAL,
                    'description': (
                        f'Multiple Valid Paid orders exist on opportunity {ord_obj.opportunity_id}; '
                        f'order {ord_obj.id} (${ord_obj.revenue} {ord_obj.currency}) risks double-counting.'
                    ),
                    'expected_decision': (
                        f'Verify or mark secondary order {ord_obj.id} as Duplicate if settlement overlaps.'
                    ),
                    'actual_decision': 'Multiple Valid Paid orders detected on one opportunity.',
                    'created_date': ord_obj.order_date,
                }
            )
    return candidates


def _detect_post_conversion_touchpoints() -> list[dict]:
    """Problem 2: Touchpoint occurring after conversion or mistakenly credited in AttributionResult."""
    candidates: list[dict] = []
    seen_tp_ids: set[str] = set()

    earliest_order_by_contact: dict[str, Order] = {}
    valid_orders = Order.objects.filter(
        verification_status=Order.VerificationStatus.VALID,
        payment_status=Order.PaymentStatus.PAID,
    ).order_by('order_date', 'id')
    for ord_obj in valid_orders:
        earliest_order_by_contact.setdefault(ord_obj.contact_id, ord_obj)

    bad_attributed_tp_ids = set(
        AttributionResult.objects.filter(touchpoint__is_post_conversion=True).values_list(
            'touchpoint_id', flat=True
        )
    )

    post_flagged = Touchpoint.objects.filter(is_post_conversion=True).select_related('contact')
    for tp in post_flagged:
        seen_tp_ids.add(tp.id)
        was_attributed = tp.id in bad_attributed_tp_ids
        candidates.append(
            {
                'issue_type': DataException.IssueType.POST_CONVERSION_TOUCH,
                'entity_type': DataException.EntityType.TOUCHPOINT,
                'entity_id': tp.id,
                'severity': DataException.Severity.HIGH,
                'description': (
                    f'Touchpoint {tp.id} ({tp.interaction_type} at {tp.timestamp.isoformat()}) occurred '
                    f'post-conversion for contact {tp.contact_id}.'
                ),
                'expected_decision': (
                    'Exclude post-conversion touchpoints (timestamp > order cutoff) from attribution.'
                ),
                'actual_decision': (
                    'CRITICAL: Incorrectly attributed in AttributionResult!'
                    if was_attributed
                    else 'Marked is_post_conversion=True and excluded by attribution engine.'
                ),
                'created_date': tp.timestamp.date(),
            }
        )

    # Also catch touchpoints timestamped after the contact's valid order even if flag was false
    if earliest_order_by_contact:
        tps = Touchpoint.objects.filter(
            contact_id__in=list(earliest_order_by_contact.keys()),
            is_post_conversion=False,
        )
        for tp in tps:
            if tp.id in seen_tp_ids:
                continue
            ord_obj = earliest_order_by_contact[tp.contact_id]
            cutoff = datetime(
                ord_obj.order_date.year,
                ord_obj.order_date.month,
                ord_obj.order_date.day,
                23,
                59,
                59,
                tzinfo=dt_timezone.utc,
            )
            tp_ts = tp.timestamp
            if tp_ts.tzinfo is None:
                tp_ts = tp_ts.replace(tzinfo=dt_timezone.utc)
            if tp_ts > cutoff:
                seen_tp_ids.add(tp.id)
                candidates.append(
                    {
                        'issue_type': DataException.IssueType.POST_CONVERSION_TOUCH,
                        'entity_type': DataException.EntityType.TOUCHPOINT,
                        'entity_id': tp.id,
                        'severity': DataException.Severity.HIGH,
                        'description': (
                            f'Touchpoint {tp.id} ({tp_ts.isoformat()}) occurred after order {ord_obj.id} '
                            f'({ord_obj.order_date.isoformat()}) for contact {tp.contact_id} without post-conversion flag.'
                        ),
                        'expected_decision': 'Mark is_post_conversion=True and exclude from pre-conversion journeys.',
                        'actual_decision': 'Detected post-cutoff timestamp automatically blocked during run evaluation.',
                        'created_date': tp_ts.date(),
                    }
                )
    return candidates


def _detect_currency_mismatches() -> list[dict]:
    """Problem 3: CostRecord currency differs from target Campaign currency."""
    candidates: list[dict] = []
    mismatched = CostRecord.objects.select_related('campaign').order_by('id')
    for cost in mismatched:
        if cost.currency != cost.campaign.currency:
            candidates.append(
                {
                    'issue_type': DataException.IssueType.CURRENCY_MISMATCH,
                    'entity_type': DataException.EntityType.COST,
                    'entity_id': cost.id,
                    'severity': DataException.Severity.MEDIUM,
                    'description': (
                        f'Cost record {cost.id} ({cost.amount} {cost.currency}) does not match '
                        f'campaign {cost.campaign_id} ({cost.campaign.currency}).'
                    ),
                    'expected_decision': (
                        f'Normalize FX or re-book spend into campaign currency ({cost.campaign.currency}) '
                        'before computing ROI/ROAS.'
                    ),
                    'actual_decision': (
                        f'Isolated {cost.currency} entry from {cost.campaign.currency} spend aggregations.'
                    ),
                    'created_date': cost.spend_date,
                }
            )
    return candidates


def _detect_omitted_campaign_costs() -> list[dict]:
    """Problem 4: Paid campaign with budget and active touchpoints/leads but zero cost records."""
    candidates: list[dict] = []
    spend_totals = {
        row['campaign_id']: row['total']
        for row in CostRecord.objects.order_by()
        .values('campaign_id')
        .annotate(total=Sum('amount'))
    }
    tp_counts = {
        row['campaign_id']: row['cnt']
        for row in Touchpoint.objects.filter(campaign_id__isnull=False)
        .order_by()
        .values('campaign_id')
        .annotate(cnt=Count('id'))
    }
    for cmp_obj in Campaign.objects.filter(is_paid_campaign=True).order_by('id'):
        total_cost = spend_totals.get(cmp_obj.id) or 0
        tp_cnt = tp_counts.get(cmp_obj.id, 0)
        if cmp_obj.budget > 0 and total_cost == 0 and tp_cnt > 0:
            candidates.append(
                {
                    'issue_type': DataException.IssueType.COSTS_OMITTED,
                    'entity_type': DataException.EntityType.CAMPAIGN,
                    'entity_id': cmp_obj.id,
                    'severity': DataException.Severity.HIGH,
                    'description': (
                        f'Paid campaign {cmp_obj.id} ({cmp_obj.name}) has budget {cmp_obj.budget} '
                        f'{cmp_obj.currency} and {tp_cnt} active touchpoints, but zero CostRecord entries.'
                    ),
                    'expected_decision': (
                        'Guard ROI against division by zero and log missing marketing spend ledger items.'
                    ),
                    'actual_decision': 'Flagged missing_cost_alert=True; ROI/ROAS safely returned as None.',
                    'created_date': cmp_obj.start_date,
                }
            )
    return candidates


def _detect_unverified_session_links() -> list[dict]:
    """Problem 5: Anonymous or Unverified WebSession linked to a Contact without deterministic evidence."""
    candidates: list[dict] = []
    sessions = WebSession.objects.all().order_by('id')
    for ses in sessions:
        unverified = (
            ses.identity_status == WebSession.IdentityStatus.UNVERIFIED_LINK
            or (ses.contact_id is not None and not ses.has_evidence)
            or (ses.contact_id is not None and ses.identity_status != WebSession.IdentityStatus.IDENTIFIED)
        )
        if unverified:
            candidates.append(
                {
                    'issue_type': DataException.IssueType.UNVERIFIED_SESSION_LINK,
                    'entity_type': DataException.EntityType.SESSION,
                    'entity_id': ses.id,
                    'severity': DataException.Severity.LOW,
                    'description': (
                        f'Web session {ses.id} (anonymous_id={ses.anonymous_id}) is linked to contact '
                        f'{ses.contact_id or "None"} with identity_status={ses.identity_status} and '
                        f'has_evidence={ses.has_evidence}.'
                    ),
                    'expected_decision': (
                        'Keep session unlinked/excluded from attribution until verified evidence exists.'
                    ),
                    'actual_decision': (
                        'Excluded session touchpoints from attribution credit calculations.'
                    ),
                    'created_date': ses.timestamp.date(),
                }
            )
    return candidates


def scan_data_quality_candidates() -> list[dict]:
    """Collect all current anomaly candidates across all 5 detection rules without mutating DB."""
    return (
        _detect_duplicate_revenue_candidates()
        + _detect_post_conversion_touchpoints()
        + _detect_currency_mismatches()
        + _detect_omitted_campaign_costs()
        + _detect_unverified_session_links()
    )


@transaction.atomic
def detect_and_sync_exceptions(*, actor=None, source_ip: str | None = None) -> dict:
    """
    Scan all 5 data-quality dimensions, insert newly discovered DataException records
    without duplicating open/reviewed issues, and log an AuditLog event.
    """
    candidates = scan_data_quality_candidates()
    existing_keys = set(
        DataException.objects.exclude(
            resolution_status=DataException.ResolutionStatus.RESOLVED
        ).values_list('issue_type', 'entity_type', 'entity_id')
    )
    resolved_keys = set(
        DataException.objects.filter(
            resolution_status=DataException.ResolutionStatus.RESOLVED
        ).values_list('issue_type', 'entity_type', 'entity_id')
    )

    to_create: list[dict] = []
    for cand in candidates:
        key = (cand['issue_type'], cand['entity_type'], cand['entity_id'])
        if key not in existing_keys and key not in resolved_keys:
            existing_keys.add(key)
            to_create.append(cand)

    created_ids: list[str] = []
    if to_create:
        batch_ids = generate_deterministic_id_batch(
            prefix='EXC',
            model_cls=DataException,
            count=len(to_create),
        )
        objs = [
            DataException(
                id=exc_id,
                issue_type=cand['issue_type'],
                entity_type=cand['entity_type'],
                entity_id=cand['entity_id'],
                severity=cand['severity'],
                description=cand['description'],
                expected_decision=cand['expected_decision'],
                actual_decision=cand['actual_decision'],
                resolution_status=DataException.ResolutionStatus.OPEN,
                created_date=cand.get('created_date') or timezone.localdate(),
            )
            for exc_id, cand in zip(batch_ids, to_create)
        ]
        DataException.objects.bulk_create(objs)
        created_ids = batch_ids

    by_issue_type: dict[str, int] = {choice.value: 0 for choice in DataException.IssueType}
    for cand in candidates:
        by_issue_type[cand['issue_type']] = by_issue_type.get(cand['issue_type'], 0) + 1

    resolved_actor = actor if (actor and getattr(actor, 'is_authenticated', False)) else None
    record_audit_log(
        entity_type='DataExceptionScan',
        entity_id=timezone.now().strftime('%Y%m%d%H%M%S'),
        action=AuditLog.Action.EXCEPTION_ACTION,
        actor=resolved_actor,
        previous_state=None,
        new_state={
            'detected_candidates': len(candidates),
            'created_exceptions': len(created_ids),
            'created_ids': created_ids[:20],
            'by_issue_type': by_issue_type,
        },
        changed_fields=['exceptions'],
        source_ip=source_ip,
        notes=f'Scanned workspace anomalies: {len(candidates)} detected, {len(created_ids)} newly logged.',
    )

    return {
        'detected_candidates': len(candidates),
        'created_count': len(created_ids),
        'created_ids': created_ids,
        'by_issue_type': by_issue_type,
    }

