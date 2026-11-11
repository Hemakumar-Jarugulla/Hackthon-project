"""Creative asset management, M2M campaign assignment, and audit trail services."""

from django.db import transaction

from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign, CampaignCreative
from apps.creatives.models import Creative
from common.audit import record_audit_log


def serialize_creative_snapshot(creative: Creative) -> dict:
    """Capture scalar fields for AuditLog tracking."""
    return {
        'id': creative.id,
        'name': creative.name,
        'primary_campaign_id': creative.primary_campaign_id,
        'creative_type': creative.creative_type,
        'status': creative.status,
        'start_date': creative.start_date.isoformat() if creative.start_date else None,
        'end_date': creative.end_date.isoformat() if creative.end_date else None,
    }


def _sync_creative_campaigns(creative: Creative, campaign_ids: list[str] | None):
    """Synchronize CampaignCreative M2M bridge entries when campaign_ids are supplied."""
    if campaign_ids is None:
        return
    resolved_ids = list(dict.fromkeys(campaign_ids))
    CampaignCreative.objects.filter(creative=creative).delete()
    if not resolved_ids:
        return
    campaigns_by_id = Campaign.objects.in_bulk(resolved_ids)
    rows = [
        CampaignCreative(
            campaign=campaigns_by_id[cid],
            creative=creative,
            is_primary=(cid == creative.primary_campaign_id),
        )
        for cid in resolved_ids
    ]
    CampaignCreative.objects.bulk_create(rows)


@transaction.atomic
def create_creative(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Creative:
    """Create a Creative asset and optionally link it to Campaigns via CampaignCreative."""
    campaign_ids = validated_data.pop('campaign_ids', None)
    creative = Creative.objects.create(**validated_data)

    if campaign_ids is None and creative.primary_campaign_id:
        campaign_ids = [creative.primary_campaign_id]
    _sync_creative_campaigns(creative, campaign_ids)

    snapshot = serialize_creative_snapshot(creative)
    record_audit_log(
        entity_type='Creative',
        entity_id=creative.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes='Creative created.',
    )
    return creative


@transaction.atomic
def update_creative(
    *,
    creative: Creative,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Creative:
    """Update Creative metadata, optional M2M links, and AuditLog history."""
    previous_state = serialize_creative_snapshot(creative)
    campaign_ids = validated_data.pop('campaign_ids', None)

    changed_fields = []
    for field, val in validated_data.items():
        if getattr(creative, field) != val:
            setattr(creative, field, val)
            changed_fields.append(field)

    if changed_fields:
        creative.save()

    if campaign_ids is not None:
        _sync_creative_campaigns(creative, campaign_ids)
        changed_fields.append('campaigns')

    if changed_fields:
        action = (
            AuditLog.Action.STATUS_CHANGE
            if 'status' in changed_fields
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Creative',
            entity_id=creative.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_creative_snapshot(creative),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes='Creative updated.',
        )
    return creative


@transaction.atomic
def delete_creative(*, creative: Creative, actor=None, source_ip: str | None = None):
    """Delete Creative asset (Touchpoint.creative defaults to SET_NULL) and audit the action."""
    snapshot = serialize_creative_snapshot(creative)
    cid = creative.id
    creative.delete()
    record_audit_log(
        entity_type='Creative',
        entity_id=cid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Creative deleted.',
    )

