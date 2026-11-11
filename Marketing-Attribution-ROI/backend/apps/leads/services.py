"""Lead lifecycle management, qualification status history, audit logging, and safe deletion."""

from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.leads.models import Lead, LeadStatusHistory
from common.audit import record_audit_log
from common.exceptions import ConflictException


def serialize_lead_snapshot(lead: Lead) -> dict:
    """Capture scalar Lead fields for AuditLog comparison."""
    return {
        'id': lead.id,
        'contact_id': lead.contact_id,
        'campaign_id': lead.campaign_id,
        'source': lead.source,
        'score': lead.score,
        'created_date': lead.created_date.isoformat() if lead.created_date else None,
        'status': lead.status,
        'converted_at': lead.converted_at.isoformat() if lead.converted_at else None,
    }


@transaction.atomic
def create_lead(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Lead:
    """Create a Lead, set converted_at when applicable, and record status history + AuditLog."""
    reason = validated_data.pop('status_reason', '') or 'Lead created.'
    if not validated_data.get('created_date'):
        validated_data['created_date'] = timezone.localdate()

    if (
        validated_data.get('status') == Lead.Status.CONVERTED
        and not validated_data.get('converted_at')
    ):
        validated_data['converted_at'] = timezone.now()

    lead = Lead.objects.create(**validated_data)

    LeadStatusHistory.objects.create(
        lead=lead,
        previous_status='',
        new_status=lead.status,
        notes=reason,
    )
    snapshot = serialize_lead_snapshot(lead)
    record_audit_log(
        entity_type='Lead',
        entity_id=lead.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes=reason,
    )
    return lead


@transaction.atomic
def update_lead(
    *,
    lead: Lead,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Lead:
    """Update Lead attributes, log status transitions, and persist AuditLog diff."""
    previous_state = serialize_lead_snapshot(lead)
    previous_status = lead.status
    reason = validated_data.pop('status_reason', '')

    changed_fields = []
    for field, value in validated_data.items():
        if getattr(lead, field) != value:
            setattr(lead, field, value)
            changed_fields.append(field)

    if lead.status == Lead.Status.CONVERTED and lead.converted_at is None:
        lead.converted_at = timezone.now()
        changed_fields.append('converted_at')

    dedup_changed = list(dict.fromkeys(changed_fields))
    if dedup_changed:
        lead.save()

    if lead.status != previous_status:
        note = reason or f'Lead status moved from {previous_status} to {lead.status}.'
        LeadStatusHistory.objects.create(
            lead=lead,
            previous_status=previous_status,
            new_status=lead.status,
            notes=note,
        )

    if dedup_changed:
        action = (
            AuditLog.Action.STATUS_CHANGE
            if lead.status != previous_status
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Lead',
            entity_id=lead.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_lead_snapshot(lead),
            changed_fields=dedup_changed,
            source_ip=source_ip,
            notes=reason or 'Lead updated.',
        )
    return lead


@transaction.atomic
def delete_lead_safely(*, lead: Lead, actor=None, source_ip: str | None = None):
    """Delete an unreferenced Lead or raise HTTP 409 Conflict when opportunities exist."""
    snapshot = serialize_lead_snapshot(lead)
    lid = lead.id
    try:
        lead.delete()
    except ProtectedError as exc:
        raise ConflictException(
            'Cannot delete this lead because dependent opportunities reference it.'
        ) from exc

    record_audit_log(
        entity_type='Lead',
        entity_id=lid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Lead deleted.',
    )

