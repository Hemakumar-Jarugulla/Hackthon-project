"""Opportunity pipeline management, stage history tracking, audit logging, and safe deletion."""

from django.db import transaction
from django.db.models import ProtectedError

from apps.audit.models import AuditLog
from apps.opportunities.models import Opportunity, OpportunityStageHistory
from common.audit import record_audit_log
from common.exceptions import ConflictException


def serialize_opportunity_snapshot(opportunity: Opportunity) -> dict:
    """Capture scalar Opportunity fields for AuditLog tracking."""
    return {
        'id': opportunity.id,
        'lead_id': opportunity.lead_id,
        'contact_id': opportunity.contact_id,
        'name': opportunity.name,
        'stage': opportunity.stage,
        'expected_revenue': str(opportunity.expected_revenue),
        'actual_revenue': str(opportunity.actual_revenue),
        'closing_date': opportunity.closing_date.isoformat() if opportunity.closing_date else None,
        'status': opportunity.status,
    }


@transaction.atomic
def create_opportunity(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Opportunity:
    """Create an Opportunity, log initial stage history, and record AuditLog."""
    opportunity = Opportunity.objects.create(**validated_data)

    OpportunityStageHistory.objects.create(
        opportunity=opportunity,
        previous_stage='',
        new_stage=opportunity.stage,
    )
    snapshot = serialize_opportunity_snapshot(opportunity)
    record_audit_log(
        entity_type='Opportunity',
        entity_id=opportunity.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes=f'Opportunity created ({opportunity.stage}).',
    )
    return opportunity


@transaction.atomic
def update_opportunity(
    *,
    opportunity: Opportunity,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Opportunity:
    """Update Opportunity pipeline fields, log stage changes, and persist AuditLog diff."""
    previous_state = serialize_opportunity_snapshot(opportunity)
    previous_stage = opportunity.stage

    changed_fields = []
    for field, value in validated_data.items():
        if getattr(opportunity, field) != value:
            setattr(opportunity, field, value)
            changed_fields.append(field)

    if changed_fields:
        opportunity.save()

    if opportunity.stage != previous_stage:
        OpportunityStageHistory.objects.create(
            opportunity=opportunity,
            previous_stage=previous_stage,
            new_stage=opportunity.stage,
        )

    if changed_fields:
        action = (
            AuditLog.Action.STATUS_CHANGE
            if ('stage' in changed_fields or 'status' in changed_fields)
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Opportunity',
            entity_id=opportunity.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_opportunity_snapshot(opportunity),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes=f'Opportunity updated ({opportunity.stage}).',
        )
    return opportunity


@transaction.atomic
def delete_opportunity_safely(
    *,
    opportunity: Opportunity,
    actor=None,
    source_ip: str | None = None,
):
    """Delete an unreferenced Opportunity or raise HTTP 409 Conflict if orders exist."""
    snapshot = serialize_opportunity_snapshot(opportunity)
    oid = opportunity.id
    try:
        opportunity.delete()
    except ProtectedError as exc:
        raise ConflictException(
            'Cannot delete this opportunity because dependent orders reference it.'
        ) from exc

    record_audit_log(
        entity_type='Opportunity',
        entity_id=oid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Opportunity deleted.',
    )

