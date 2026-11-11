"""Audience management, M2M campaign assignment, archiving, and audit logging services."""

from django.db import transaction

from apps.audiences.models import Audience
from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign, CampaignAudience
from common.audit import record_audit_log


def serialize_audience_snapshot(audience: Audience) -> dict:
    """Capture scalar fields for AuditLog tracking."""
    return {
        'id': audience.id,
        'name': audience.name,
        'audience_type': audience.audience_type,
        'estimated_size': audience.estimated_size,
        'status': audience.status,
        'effective_from': audience.effective_from.isoformat() if audience.effective_from else None,
        'effective_to': audience.effective_to.isoformat() if audience.effective_to else None,
    }


def _sync_audience_campaigns(audience: Audience, campaign_ids: list[str] | None):
    """Synchronize CampaignAudience M2M bridge entries when campaign_ids are supplied."""
    if campaign_ids is None:
        return
    resolved_ids = list(dict.fromkeys(campaign_ids))
    CampaignAudience.objects.filter(audience=audience).delete()
    if not resolved_ids:
        return
    campaigns_by_id = Campaign.objects.in_bulk(resolved_ids)
    rows = [
        CampaignAudience(
            campaign=campaigns_by_id[cid],
            audience=audience,
        )
        for cid in resolved_ids
    ]
    CampaignAudience.objects.bulk_create(rows)


@transaction.atomic
def create_audience(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Audience:
    """Create an Audience segment and optionally assign Campaigns via CampaignAudience."""
    campaign_ids = validated_data.pop('campaign_ids', None)
    audience = Audience.objects.create(**validated_data)
    _sync_audience_campaigns(audience, campaign_ids)

    snapshot = serialize_audience_snapshot(audience)
    record_audit_log(
        entity_type='Audience',
        entity_id=audience.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes='Audience created.',
    )
    return audience


@transaction.atomic
def update_audience(
    *,
    audience: Audience,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Audience:
    """Update Audience fields, optional M2M links, and AuditLog history."""
    previous_state = serialize_audience_snapshot(audience)
    campaign_ids = validated_data.pop('campaign_ids', None)

    changed_fields = []
    for field, val in validated_data.items():
        if getattr(audience, field) != val:
            setattr(audience, field, val)
            changed_fields.append(field)

    if changed_fields:
        audience.save()

    if campaign_ids is not None:
        _sync_audience_campaigns(audience, campaign_ids)
        changed_fields.append('campaigns')

    if changed_fields:
        action = (
            AuditLog.Action.STATUS_CHANGE
            if 'status' in changed_fields
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Audience',
            entity_id=audience.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_audience_snapshot(audience),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes='Audience updated.',
        )
    return audience


@transaction.atomic
def archive_audience(
    *,
    audience: Audience,
    actor=None,
    source_ip: str | None = None,
) -> Audience:
    """Soft-archive an Audience segment while preserving campaign link history."""
    if audience.status == Audience.Status.ARCHIVED:
        return audience
    previous_state = serialize_audience_snapshot(audience)
    audience.status = Audience.Status.ARCHIVED
    audience.save(update_fields=['status', 'updated_at'])
    record_audit_log(
        entity_type='Audience',
        entity_id=audience.id,
        action=AuditLog.Action.ARCHIVE,
        actor=actor,
        previous_state=previous_state,
        new_state=serialize_audience_snapshot(audience),
        changed_fields=['status'],
        source_ip=source_ip,
        notes='Audience archived.',
    )
    return audience


@transaction.atomic
def delete_audience(*, audience: Audience, actor=None, source_ip: str | None = None):
    """Delete an Audience segment and record DELETE audit event."""
    snapshot = serialize_audience_snapshot(audience)
    aid = audience.id
    audience.delete()
    record_audit_log(
        entity_type='Audience',
        entity_id=aid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Audience deleted.',
    )

