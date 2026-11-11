"""Marketing cost ledger management, FX mismatch summaries, and audit logging services."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, F, QuerySet, Sum

from apps.audit.models import AuditLog
from apps.costs.models import CostRecord
from common.audit import record_audit_log


def serialize_cost_snapshot(cost: CostRecord) -> dict:
    """Capture scalar CostRecord fields for AuditLog tracking."""
    return {
        'id': cost.id,
        'campaign_id': cost.campaign_id,
        'channel_id': cost.channel_id,
        'category': cost.category,
        'amount': str(cost.amount),
        'currency': cost.currency,
        'spend_date': cost.spend_date.isoformat() if cost.spend_date else None,
        'description': cost.description,
    }


def build_cost_summary(queryset: QuerySet[CostRecord]) -> dict:
    """
    Aggregate spend totals split by currency consistency and cost category
    across the active filtered ledger queryset.
    """
    # Clear model ordering before .values().annotate() so SQL groups purely by target columns.
    base_qs = queryset.order_by()
    total_records = base_qs.count()
    matched_qs = base_qs.filter(currency=F('campaign__currency'))
    mismatched_qs = base_qs.exclude(currency=F('campaign__currency'))

    currency_totals: dict[str, dict] = {}
    for row in base_qs.values('currency').annotate(total=Sum('amount'), cnt=Count('id')):
        curr = row['currency']
        bucket = currency_totals.setdefault(
            curr,
            {
                'currency': curr,
                'total_spend': Decimal('0.00'),
                'matched_spend': Decimal('0.00'),
                'mismatched_spend': Decimal('0.00'),
                'record_count': 0,
            },
        )
        bucket['total_spend'] += (row['total'] or Decimal('0.00')).quantize(Decimal('0.01'))
        bucket['record_count'] += row['cnt'] or 0

    for row in matched_qs.values('currency').annotate(total=Sum('amount')):
        curr = row['currency']
        if curr in currency_totals:
            currency_totals[curr]['matched_spend'] += (
                row['total'] or Decimal('0.00')
            ).quantize(Decimal('0.01'))

    for row in mismatched_qs.values('currency').annotate(total=Sum('amount')):
        curr = row['currency']
        if curr in currency_totals:
            currency_totals[curr]['mismatched_spend'] += (
                row['total'] or Decimal('0.00')
            ).quantize(Decimal('0.01'))

    by_category = [
        {
            'category': row['category'],
            'matched_spend': (row['matched'] or Decimal('0.00')).quantize(Decimal('0.01')),
            'record_count': row['cnt'],
        }
        for row in matched_qs.values('category')
        .annotate(matched=Sum('amount'), cnt=Count('id'))
        .order_by('-matched', 'category')
    ]

    return {
        'total_records': total_records,
        'matched_currency_records': matched_qs.count(),
        'mismatched_currency_records': mismatched_qs.count(),
        'spend_by_currency': sorted(currency_totals.values(), key=lambda x: x['currency']),
        'matched_spend_by_category': by_category,
    }


@transaction.atomic
def create_cost_record(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> CostRecord:
    """Create a CostRecord and persist CREATE AuditLog event."""
    cost = CostRecord.objects.create(**validated_data)
    snapshot = serialize_cost_snapshot(cost)
    record_audit_log(
        entity_type='CostRecord',
        entity_id=cost.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes=f'Cost record added ({cost.amount} {cost.currency}).',
    )
    return cost


@transaction.atomic
def update_cost_record(
    *,
    cost: CostRecord,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> CostRecord:
    """Update CostRecord attributes and persist AuditLog diff."""
    previous_state = serialize_cost_snapshot(cost)
    changed_fields = []
    for field, value in validated_data.items():
        if getattr(cost, field) != value:
            setattr(cost, field, value)
            changed_fields.append(field)

    if changed_fields:
        cost.save()
        record_audit_log(
            entity_type='CostRecord',
            entity_id=cost.id,
            action=AuditLog.Action.UPDATE,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_cost_snapshot(cost),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes='Cost record updated.',
        )
    return cost


@transaction.atomic
def delete_cost_record(*, cost: CostRecord, actor=None, source_ip: str | None = None):
    """Delete a CostRecord and log DELETE AuditLog event."""
    snapshot = serialize_cost_snapshot(cost)
    cid = cost.id
    cost.delete()
    record_audit_log(
        entity_type='CostRecord',
        entity_id=cid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Cost record deleted.',
    )

