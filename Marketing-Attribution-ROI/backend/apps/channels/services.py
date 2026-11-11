"""Channel management, audit logging, and aggregated ROI metrics services."""

from decimal import Decimal

from django.db import transaction
from django.db.models import ProtectedError

from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign
from apps.campaigns.services import get_campaign_metrics_map
from apps.channels.models import Channel
from common.audit import record_audit_log
from common.exceptions import ConflictException
from common.utils import safe_divide


def serialize_channel_snapshot(channel: Channel) -> dict:
    """Capture scalar fields for AuditLog tracking."""
    return {
        'id': channel.id,
        'name': channel.name,
        'channel_type': channel.channel_type,
        'status': channel.status,
        'owner': channel.owner,
        'description': channel.description,
    }


def get_channel_metrics_map(
    channels: list[Channel],
    *,
    model_id: str | None = None,
) -> dict[str, dict]:
    """Aggregate campaign metrics up to each Channel using O(1) batch queries."""
    if not channels:
        return {}

    channel_ids = [ch.id for ch in channels]
    campaigns = list(Campaign.objects.filter(channel_id__in=channel_ids))
    campaign_metrics = get_campaign_metrics_map(campaigns, model_id=model_id)

    agg: dict[str, dict] = {
        cid: {
            'total_campaigns': 0,
            'total_spend': Decimal('0.00'),
            'attributed_revenue': Decimal('0.00'),
            'total_leads': 0,
            'conversions_count': 0,
            'has_currency_mismatch': False,
        }
        for cid in channel_ids
    }

    for cmp in campaigns:
        bucket = agg[cmp.channel_id]
        m = campaign_metrics.get(cmp.id, {})
        bucket['total_campaigns'] += 1
        bucket['total_spend'] += m.get('spend', Decimal('0.00'))
        bucket['attributed_revenue'] += m.get('attributed_revenue', Decimal('0.00'))
        bucket['total_leads'] += m.get('leads_count', 0)
        bucket['conversions_count'] += m.get('conversions_count', 0)
        if m.get('has_currency_mismatch'):
            bucket['has_currency_mismatch'] = True

    result: dict[str, dict] = {}
    for cid, bucket in agg.items():
        spend = bucket['total_spend'].quantize(Decimal('0.01'))
        rev = bucket['attributed_revenue'].quantize(Decimal('0.01'))
        roi_raw = safe_divide((rev - spend) * Decimal('100.00'), spend)
        roas_raw = safe_divide(rev, spend)
        result[cid] = {
            'total_campaigns': bucket['total_campaigns'],
            'total_spend': spend,
            'attributed_revenue': rev,
            'total_leads': bucket['total_leads'],
            'conversions_count': bucket['conversions_count'],
            'roi': round(float(roi_raw), 2) if roi_raw is not None else None,
            'roas': round(float(roas_raw), 2) if roas_raw is not None else None,
            'has_currency_mismatch': bucket['has_currency_mismatch'],
        }
    return result


@transaction.atomic
def create_channel(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Channel:
    """Create a marketing Channel and record CREATE audit event."""
    channel = Channel.objects.create(**validated_data)
    snapshot = serialize_channel_snapshot(channel)
    record_audit_log(
        entity_type='Channel',
        entity_id=channel.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes='Channel created.',
    )
    return channel


@transaction.atomic
def update_channel(
    *,
    channel: Channel,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Channel:
    """Update Channel attributes and log field-level diff in AuditLog."""
    previous_state = serialize_channel_snapshot(channel)
    changed_fields = []
    for field, value in validated_data.items():
        if getattr(channel, field) != value:
            setattr(channel, field, value)
            changed_fields.append(field)

    if changed_fields:
        channel.save()
        action = (
            AuditLog.Action.STATUS_CHANGE
            if 'status' in changed_fields
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Channel',
            entity_id=channel.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_channel_snapshot(channel),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes='Channel updated.',
        )
    return channel


@transaction.atomic
def archive_channel(
    *,
    channel: Channel,
    actor=None,
    source_ip: str | None = None,
) -> Channel:
    """Soft-archive a Channel cleanly while keeping dependent campaign/touchpoint history intact."""
    if channel.status == Channel.Status.ARCHIVED:
        return channel
    previous_state = serialize_channel_snapshot(channel)
    channel.status = Channel.Status.ARCHIVED
    channel.save(update_fields=['status', 'updated_at'])
    record_audit_log(
        entity_type='Channel',
        entity_id=channel.id,
        action=AuditLog.Action.ARCHIVE,
        actor=actor,
        previous_state=previous_state,
        new_state=serialize_channel_snapshot(channel),
        changed_fields=['status'],
        source_ip=source_ip,
        notes='Channel archived.',
    )
    return channel


@transaction.atomic
def delete_channel_safely(*, channel: Channel, actor=None, source_ip: str | None = None):
    """Delete unreferenced Channel or raise 409 Conflict if protected campaigns/records exist."""
    snapshot = serialize_channel_snapshot(channel)
    cid = channel.id
    try:
        channel.delete()
    except ProtectedError as exc:
        raise ConflictException(
            'Cannot delete this channel because campaigns, touchpoints, or cost records reference it. '
            'Archive the channel instead via POST /api/v1/channels/{id}/archive/.'
        ) from exc

    record_audit_log(
        entity_type='Channel',
        entity_id=cid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Channel deleted.',
    )

